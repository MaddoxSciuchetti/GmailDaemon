import { spawn } from "node:child_process";
import path from "node:path";
import { NextResponse } from "next/server";

const root = path.resolve(process.cwd(), "..");
const python = path.join(root, ".venv", "bin", "python");

function runCli(args: string[], input?: string): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const child = spawn(python, ["-m", "gmail_daemon.proposal_cli", ...args], { cwd: root });
    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (chunk) => {
      stdout += chunk;
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk;
    });
    child.on("close", (code) => {
      if (code !== 0) {
        reject(new Error(stderr || `proposal_cli exited with ${code}`));
        return;
      }
      resolve(stdout ? JSON.parse(stdout) : {});
    });

    if (input) {
      child.stdin.write(input);
      child.stdin.end();
    }
  });
}

export async function GET() {
  const proposals = await runCli(["list"]);
  return NextResponse.json({ proposals });
}

export async function POST(request: Request) {
  const body = await request.json();

  if (body.action === "accept") {
    const proposal = await runCli(["accept", body.id]);
    return NextResponse.json({ proposal });
  }

  if (body.action === "decline") {
    const proposal = await runCli(["decline", body.id, "--text", body.text || ""]);
    return NextResponse.json({ proposal });
  }

  return NextResponse.json({ error: "Unknown action" }, { status: 400 });
}
