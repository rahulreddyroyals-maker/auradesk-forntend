"use client";

import { useEffect, useState } from "react";
import { TopBar } from "@/components/shared/top-bar";
import { EmptyState } from "@/components/shared/empty-state";
import { Button } from "@/components/ui/button";
import { Card, Input, Label, Textarea } from "@/components/ui/primitives";
import { apiGet, apiPost, apiPatch, apiDelete } from "@/lib/api-client";
import { BookOpen, Plus, Trash2, Pencil, Check, X } from "lucide-react";

interface KBArticle {
  id: string;
  category: string;
  question: string;
  answer: string;
  source: string;
  updated_at: string;
  embedded: boolean;
}

export default function KnowledgeBasePage() {
  const [articles, setArticles] = useState<KBArticle[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState({ category: "pricing", question: "", answer: "" });
  const [saving, setSaving] = useState(false);

  async function load() {
    try {
      const data = await apiGet<KBArticle[]>("/knowledge-base");
      setArticles(data);
    } catch {
      setError("Couldn't load your knowledge base. Is the backend running?");
    }
  }

  useEffect(() => {
    load();
  }, []);

  function startCreate() {
    setEditingId(null);
    setForm({ category: "pricing", question: "", answer: "" });
    setShowForm(true);
  }

  function startEdit(article: KBArticle) {
    setEditingId(article.id);
    setForm({ category: article.category, question: article.question, answer: article.answer });
    setShowForm(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      if (editingId) {
        await apiPatch(`/knowledge-base/${editingId}`, form);
      } else {
        await apiPost("/knowledge-base", form);
      }
      setShowForm(false);
      await load();
    } catch {
      setError("Couldn't save that article. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await apiDelete(`/knowledge-base/${id}`);
      await load();
    } catch {
      setError("Couldn't delete that article.");
    }
  }

  return (
    <>
      <TopBar title="Knowledge Base" />
      <main className="flex flex-1 flex-col p-8 gap-6">
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground max-w-lg">
            This is what your AI Employee answers pricing, policy, and FAQ questions from —
            it never guesses beyond what&apos;s written here.
          </p>
          {!showForm && (
            <Button onClick={startCreate}>
              <Plus className="h-4 w-4" /> Add article
            </Button>
          )}
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        {showForm && (
          <Card>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="category">Category</Label>
                <Input
                  id="category"
                  required
                  value={form.category}
                  onChange={(e) => setForm({ ...form, category: e.target.value })}
                  placeholder="pricing / policy / hours / service"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="question">Question</Label>
                <Input
                  id="question"
                  required
                  value={form.question}
                  onChange={(e) => setForm({ ...form, question: e.target.value })}
                  placeholder="How much does Botox cost?"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="answer">Answer</Label>
                <Textarea
                  id="answer"
                  required
                  rows={4}
                  value={form.answer}
                  onChange={(e) => setForm({ ...form, answer: e.target.value })}
                  placeholder="Botox starts at $12/unit, with a typical treatment area running $200–$400..."
                />
              </div>
              <div className="flex gap-2">
                <Button type="submit" disabled={saving}>
                  <Check className="h-4 w-4" /> {saving ? "Saving…" : "Save"}
                </Button>
                <Button type="button" variant="secondary" onClick={() => setShowForm(false)}>
                  <X className="h-4 w-4" /> Cancel
                </Button>
              </div>
            </form>
          </Card>
        )}

        {articles === null && !error && <p className="text-sm text-muted-foreground">Loading…</p>}

        {articles !== null && articles.length === 0 && (
          <EmptyState
            icon={BookOpen}
            title="No articles yet"
            description="Add your first FAQ, pricing, or policy article so your AI Employee has something to answer from."
          />
        )}

        {articles !== null && articles.length > 0 && (
          <div className="space-y-3">
            {articles.map((article) => (
              <Card key={article.id} className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <span className="inline-block rounded-full bg-aura-gold-500/10 px-2.5 py-0.5 text-[11px] font-medium uppercase tracking-wide text-aura-gold-700 mb-1.5">
                    {article.category}
                  </span>
                  <p className="font-medium text-sm">{article.question}</p>
                  <p className="text-sm text-muted-foreground mt-1">{article.answer}</p>
                </div>
                <div className="flex shrink-0 gap-1">
                  <button
                    onClick={() => startEdit(article)}
                    className="rounded-full p-2 hover:bg-muted"
                    aria-label="Edit"
                  >
                    <Pencil className="h-4 w-4 text-muted-foreground" />
                  </button>
                  <button
                    onClick={() => handleDelete(article.id)}
                    className="rounded-full p-2 hover:bg-muted"
                    aria-label="Delete"
                  >
                    <Trash2 className="h-4 w-4 text-muted-foreground" />
                  </button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </main>
    </>
  );
}
