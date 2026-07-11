"use client";

import { useEffect, useMemo, useState } from "react";
import { Check, RefreshCw, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

type Proposal = {
  id: string;
  sender: string;
  subject: string;
  reason: string;
  task_title: string;
  proposed_reply: string;
  original_text: string;
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
  const visible = useMemo(() => proposals.filter((item) => item.status !== "ignored"), [proposals]);

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
    <main className="min-h-screen bg-white px-5 py-8 text-black md:px-12">
      <section className="mx-auto flex max-w-5xl flex-col gap-8">
        <header className="flex flex-col gap-5 border-b border-black pb-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <Badge variant="outline">{pending.length} pending</Badge>
            <h1 className="mt-4 text-3xl font-semibold tracking-normal">Email proposals</h1>
            <p className="mt-2 text-sm text-neutral-600">Review generated replies before they are sent.</p>
          </div>
          <Button variant="outline" onClick={load} disabled={loading}>
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
        </header>

        <div className="grid gap-4">
          {visible.map((proposal) => (
            <Card key={proposal.id}>
              <CardHeader className="gap-4 sm:flex-row sm:items-start sm:justify-between sm:space-y-0">
                <div className="min-w-0 space-y-2">
                  <Badge variant="secondary">{proposal.reason}</Badge>
                  <CardTitle className="truncate">{proposal.subject || "(no subject)"}</CardTitle>
                  <CardDescription>{proposal.sender}</CardDescription>
                </div>
                {proposal.status === "proposed" ? (
                  <div className="flex shrink-0 gap-2">
                    <Button onClick={() => act("accept", proposal)} disabled={loading} size="sm">
                      <Check className="h-4 w-4" />
                      Accept
                    </Button>
                    <Button variant="outline" onClick={() => setSelected(proposal)} disabled={loading} size="sm">
                      <X className="h-4 w-4" />
                      Decline
                    </Button>
                  </div>
                ) : (
                  <Badge variant="outline">{proposal.status}</Badge>
                )}
              </CardHeader>

              <CardContent className="space-y-4">
                <section>
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-neutral-500">
                    What they wrote
                  </p>
                  <div className="max-h-56 overflow-auto whitespace-pre-wrap rounded-2xl border border-black bg-white p-4 text-sm leading-6 text-neutral-900">
                    {proposal.original_text || "No email body was available."}
                  </div>
                </section>

                <section>
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-neutral-500">
                    Proposed response
                  </p>
                  <div className="whitespace-pre-wrap rounded-2xl border border-neutral-200 bg-neutral-50 p-4 text-sm leading-6 text-neutral-900">
                    {proposal.proposed_reply}
                  </div>
                </section>
              </CardContent>
            </Card>
          ))}

          {!visible.length && (
            <Card>
              <CardContent className="p-10 text-center">
                <p className="text-sm text-neutral-600">No proposals yet.</p>
              </CardContent>
            </Card>
          )}
        </div>
      </section>

      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-5">
          <Card className="w-full max-w-xl">
            <CardHeader>
              <CardTitle>Write your own response</CardTitle>
              <CardDescription>{selected.subject || selected.sender}</CardDescription>
            </CardHeader>
            <CardContent>
              <Textarea
                value={replacement}
                onChange={(event) => setReplacement(event.target.value)}
                placeholder="Enter your replacement text"
              />
            </CardContent>
            <CardFooter className="justify-end gap-2">
              <Button variant="outline" onClick={() => setSelected(null)}>
                Cancel
              </Button>
              <Button onClick={() => act("decline", selected, replacement)} disabled={!replacement.trim()}>
                Save
              </Button>
            </CardFooter>
          </Card>
        </div>
      )}
    </main>
  );
}
