mod kernel;
mod manifest;
mod neural;
mod ollama;
mod policy;
mod rpc;
mod server;

use manifest::{default_connector_dirs, discover_connectors, find_tool, RegisteredConnector};
use ollama::{initial_history, run_agent_turn, OllamaClient};
use policy::{audit_log, check_approval, ApprovalMode};
use rpc::call_stdio_tool;
use serde_json::{json, Value};
use std::env;
use std::io::{self, Write};
use std::process;

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    let connectors = discover_connectors(&default_connector_dirs());

    let code = match args.first().map(String::as_str) {
        None | Some("serve") => {
            let model = parse_flag(&args, "--model");
            if let Err(err) = server::serve_socket(connectors, model) {
                eprintln!("Error: {err}");
                1
            } else {
                0
            }
        }
        Some("list") => {
            print_connectors(&connectors);
            0
        }
        Some("kernel") => {
            let k = kernel::KernelTelemetry::collect();
            println!(
                "{}",
                serde_json::to_string_pretty(&k.to_json()).unwrap_or_default()
            );
            0
        }
        Some("optimize") => {
            let res = kernel::optimize_kernel_memory();
            println!(
                "{}",
                serde_json::to_string_pretty(&res).unwrap_or_default()
            );
            0
        }
        Some("call") => run_direct_call(&connectors, &args[1..]),
        Some("ask") => run_ask(&connectors, &args[1..]),
        Some("chat") => run_chat(&connectors, &args[1..]),
        Some("-h") | Some("--help") | Some("help") => {
            print_usage();
            0
        }
        Some(other) => {
            eprintln!("Unknown subcommand: {other}");
            print_usage();
            2
        }
    };

    if code != 0 {
        process::exit(code);
    }
}

fn print_usage() {
    println!(
        "aria-daemon v0.1.0 - OS-native AI broker for AriaOS\n\n\
         Usage:\n  \
         aria-daemon serve [--model <name>]               Start Unix socket daemon\n  \
         aria-daemon list                                 List discovered connectors and tools\n  \
         aria-daemon call <connector> <tool> [json_args]  Execute a connector tool directly\n  \
         aria-daemon ask \"<prompt>\" [--model <name>] [--yes]  Run one prompt through Ollama\n  \
         aria-daemon chat [--model <name>] [--yes]        Interactive terminal assistant"
    );
}

fn print_connectors(connectors: &[RegisteredConnector]) {
    println!("Discovered {} connector(s):", connectors.len());
    for c in connectors {
        println!(
            "  - {} v{} [tier={}, transport={}]",
            c.manifest.id, c.manifest.version, c.manifest.tier, c.manifest.transport
        );
        for t in &c.manifest.tools {
            println!(
                "      * {} (risk={}): {}",
                t.name,
                t.risk_level.as_str(),
                t.description
            );
        }
    }
}

fn run_direct_call(connectors: &[RegisteredConnector], args: &[String]) -> i32 {
    if args.len() < 2 {
        eprintln!("Usage: aria-daemon call <connector> <tool> [json_args] [--yes]");
        return 2;
    }
    let conn_id = &args[0];
    let tool_name = &args[1];
    let auto_yes = args.iter().any(|a| a == "--yes");
    let raw_json = args
        .get(2)
        .filter(|a| !a.starts_with("--"))
        .map(String::as_str)
        .unwrap_or("{}");

    let parsed_args: Value = match serde_json::from_str(raw_json) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("Invalid JSON arguments: {e}");
            return 2;
        }
    };

    let Some((conn, spec)) = find_tool(connectors, conn_id, tool_name) else {
        eprintln!("Unknown connector '{conn_id}' or tool '{tool_name}'");
        return 1;
    };

    let mode = if auto_yes {
        ApprovalMode::AutoWrite
    } else {
        ApprovalMode::Interactive
    };
    if !check_approval(conn_id, tool_name, spec.risk_level, &parsed_args, mode) {
        audit_log(conn_id, tool_name, spec.risk_level, "denied", &parsed_args);
        eprintln!("Execution cancelled.");
        return 1;
    }

    match call_stdio_tool(conn, tool_name, parsed_args.clone()) {
        Ok(result) => {
            audit_log(conn_id, tool_name, spec.risk_level, "ok", &parsed_args);
            println!(
                "{}",
                serde_json::to_string_pretty(&result).unwrap_or_else(|_| json!(result).to_string())
            );
            0
        }
        Err(err) => {
            audit_log(conn_id, tool_name, spec.risk_level, "error", &parsed_args);
            eprintln!("Error: {err}");
            1
        }
    }
}

fn run_ask(connectors: &[RegisteredConnector], args: &[String]) -> i32 {
    let model = parse_flag(args, "--model");
    let auto_yes = args.iter().any(|a| a == "--yes");
    let prompt_parts: Vec<&str> = args
        .iter()
        .enumerate()
        .filter(|(i, a)| {
            *a != "--yes"
                && *a != "--model"
                && (*i == 0 || args[i - 1] != "--model")
        })
        .map(|(_, a)| a.as_str())
        .collect();

    if prompt_parts.is_empty() {
        eprintln!("Usage: aria-daemon ask \"<prompt>\" [--model <name>] [--yes]");
        return 2;
    }

    let prompt = prompt_parts.join(" ");
    let client = OllamaClient::from_env(model);
    let mut history = initial_history();
    let mode = if auto_yes {
        ApprovalMode::AutoWrite
    } else {
        ApprovalMode::Interactive
    };

    match run_agent_turn(&client, connectors, &mut history, &prompt, mode) {
        Ok(answer) => {
            println!("\nAria: {answer}");
            0
        }
        Err(err) => {
            eprintln!("Error: {err}");
            1
        }
    }
}

fn run_chat(connectors: &[RegisteredConnector], args: &[String]) -> i32 {
    let model = parse_flag(args, "--model");
    let auto_yes = args.iter().any(|a| a == "--yes");
    let client = OllamaClient::from_env(model);
    let mut history = initial_history();
    let mode = if auto_yes {
        ApprovalMode::AutoWrite
    } else {
        ApprovalMode::Interactive
    };

    println!(
        "AriaOS interactive session (model={}, connectors={}). Type 'exit' to quit.",
        client.model,
        connectors.len()
    );

    let stdin = io::stdin();
    loop {
        print!("\nyou> ");
        let _ = io::stdout().flush();

        let mut line = String::new();
        if stdin.read_line(&mut line).is_err() || line.is_empty() {
            break;
        }
        let prompt = line.trim();
        if prompt.is_empty() {
            continue;
        }
        if matches!(prompt, "exit" | "quit" | "/exit" | "/quit") {
            break;
        }

        match run_agent_turn(&client, connectors, &mut history, prompt, mode) {
            Ok(answer) => println!("\naria> {answer}"),
            Err(err) => eprintln!("\n[error] {err}"),
        }
    }
    0
}

fn parse_flag(args: &[String], flag: &str) -> Option<String> {
    args.windows(2)
        .find(|w| w[0] == flag)
        .map(|w| w[1].clone())
}
