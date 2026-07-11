"use client";

import { useEffect, useMemo, useState } from "react";
import { Check, RefreshCw, X } from "lucide-react";
import { Button } from "@/components/ui/button";

type Proposal = {
  id: string;
  sender: string;
  subject: string;
  reason: string;
  task_title: string;
  proposed_reply: string;
  labels: string[];
  status: string;
  replacement_text?: string | null;
};

export default function Home() {
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [selected, setSelected] = useState<Proposal | null>(null);
  const [replacement, setReplacement] = useState("");
  const [loading, setLoading] = useState(false);

  const pending = useMemo(() => proposals.filter((item) => item.status === "proposed"), [proposals]);

  async function load() {
    setLoading(true);
    const response = await fetch("/api/proposals", { cache: "no-store" });
    const data = await response.json();
    setProposals(data.proposals);
    setLoading(false);
  }

  async function act(action: "accept" | "decline", proposal: Proposal, text?: string) {
    setLoading(true);
    await fetch("/api/proposals", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, id: proposal.id, text }),
    });
    setSelected(null);
    setReplacement("");
    await load();
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <main className="min-h-screen bg-white px-6 py-8 text-black md:px-12">
      <section className="mx-auto flex max-w-5xl flex-col gap-8">
        <header className="flex items-center justify-between border-b border-black pb-5">
          <div>
            <h1 className="text-2xl font-semibold tracking-normal">Email proposals</h1>
            <p className="mt-1 text-sm text-neutral-600">{pending.length} pending</p>
          </div>
          <Button variant="outline" onClick={load} disabled={loading}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </header>

        <div className="grid gap-4">
          {pending.map((proposal) => (
            <article key={proposal.id} className="rounded-2xl border border-black p-5">
              <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div className="min-w-0">
                  <p className="text-xs uppercase tracking-wide text-neutral-500">{proposal.reason}</p>
                  <h2 className="mt-2 text-lg font-medium">{proposal.subject || "(no subject)"}</h2>
                  <p className="mt-1 text-sm text-neutral-600">{proposal.sender}</p>
                </div>
                <div className="flex gap-2">
                  <Button onClick={() => act("accept", proposal)} disabled={loading}>
                    <Check className="mr-2 h-4 w-4" />
                    Accept
                  </Button>
                  <Button variant="outline" onClick={() => setSelected(proposal)} disabled={loading}>
                    <X className="mr-2 h-4 w-4" />
                    Decline
                  </Button>
                </div>
              </div>

              <div className="mt-5 rounded-2xl bg-neutral-100 p-4 text-sm leading-6">
                {proposal.proposed_reply}
              </div>
            </article>
          ))}

          {!pending.length && (
            <div className="rounded-2xl border border-black p-10 text-center text-sm text-neutral-600">
              No pending proposals.
            </div>
          )}
        </div>
      </section>

      {selected && (
        <div className="fixed inset-0 flex items-center justify-center bg-black/20 p-6">
          <div className="w-full max-w-xl rounded-2xl border border-black bg-white p-6">
            <h3 className="text-lg font-medium">Write your own response</h3>
            <textarea
              className="mt-4 min-h-40 w-full rounded-2xl border border-black p-4 text-sm outline-none"
              value={replacement}
              onChange={(event) => setReplacement(event.target.value)}
              placeholder="Enter your replacement text"
            />
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="outline" onClick={() => setSelected(null)}>
                Cancel
              </Button>
              <Button onClick={() => act("decline", selected, replacement)} disabled={!replacement.trim()}>
                Save
              </Button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
