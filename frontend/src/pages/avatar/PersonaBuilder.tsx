import { useState } from "react";
import { OrgAppShell, PageTopbar } from "@/components/layout/OrgAppShell";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Label, Textarea } from "@/components/ui/Input";
import { Bot, Save } from "lucide-react";
import { cn } from "@/lib/utils";

const voices = ["Warm & conversational", "Direct & professional", "Energetic & upbeat"];
const tones = ["Friendly", "Neutral", "Formal"];
const appearances = ["Sage", "Nova", "Atlas", "Iris"];

export function PersonaBuilder() {
  const [name, setName] = useState("Ava");
  const [voice, setVoice] = useState(voices[0]);
  const [tone, setTone] = useState(tones[0]);
  const [appearance, setAppearance] = useState(appearances[0]);
  const [intro, setIntro] = useState(
    "Hi, I'm Ava — I'll be walking you through a few questions today. There are no wrong answers, just talk me through your thinking."
  );
  const [saved, setSaved] = useState(false);

  return (
    <OrgAppShell>
      <PageTopbar
        breadcrumb="Interviews"
        title="Persona Builder"
        actions={
          <Button
            onClick={() => {
              setSaved(true);
              setTimeout(() => setSaved(false), 1500);
            }}
          >
            <Save className="h-4 w-4" /> {saved ? "Saved" : "Save persona"}
          </Button>
        }
      />

      <div className="flex-1 px-8 py-6">
        <div className="grid grid-cols-3 gap-6">
          <div className="col-span-2 space-y-6">
            <Card>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="persona-name">Persona name</Label>
                  <Input id="persona-name" value={name} onChange={(e) => setName(e.target.value)} />
                </div>

                <div>
                  <Label>Appearance</Label>
                  <div className="grid grid-cols-4 gap-3">
                    {appearances.map((a) => (
                      <button
                        key={a}
                        onClick={() => setAppearance(a)}
                        className={cn(
                          "flex flex-col items-center gap-2 rounded-md border p-4 transition-colors",
                          appearance === a
                            ? "border-brand-primary bg-brand-primary-subtle"
                            : "border-neutral-200 hover:bg-neutral-50"
                        )}
                      >
                        <span
                          className={cn(
                            "flex h-12 w-12 items-center justify-center rounded-full",
                            appearance === a
                              ? "bg-brand-primary text-white"
                              : "bg-neutral-200 text-neutral-500"
                          )}
                        >
                          <Bot className="h-6 w-6" />
                        </span>
                        <span className="text-xs font-medium text-neutral-700">{a}</span>
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <Label>Voice</Label>
                  <div className="space-y-2">
                    {voices.map((v) => (
                      <label
                        key={v}
                        className="flex cursor-pointer items-center gap-2 rounded-md border border-neutral-200 px-3 py-2"
                      >
                        <input
                          type="radio"
                          name="voice"
                          checked={voice === v}
                          onChange={() => setVoice(v)}
                          className="h-4 w-4 text-brand-primary focus:ring-brand-primary/40"
                        />
                        <span className="text-sm text-neutral-700">{v}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div>
                  <Label>Tone</Label>
                  <div className="flex gap-2">
                    {tones.map((t) => (
                      <button
                        key={t}
                        onClick={() => setTone(t)}
                        className={cn(
                          "rounded-md border px-3 py-1.5 text-sm font-medium",
                          tone === t
                            ? "border-brand-primary bg-brand-primary text-white"
                            : "border-neutral-300 text-neutral-600 hover:bg-neutral-50"
                        )}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <Label htmlFor="intro">Introduction script</Label>
                  <Textarea
                    id="intro"
                    rows={4}
                    value={intro}
                    onChange={(e) => setIntro(e.target.value)}
                  />
                </div>
              </CardContent>
            </Card>
          </div>

          <Card className="h-fit">
            <CardContent>
              <h3 className="mb-3 text-sm font-semibold text-neutral-900">Preview</h3>
              <div className="flex flex-col items-center rounded-md bg-neutral-900 p-6 text-center text-white">
                <span className="mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-brand-primary to-brand-primary-hover">
                  <Bot className="h-8 w-8" />
                </span>
                <p className="text-sm font-medium">{name}</p>
                <p className="text-xs text-neutral-400">{tone} · {appearance}</p>
              </div>
              <p className="mt-3 text-sm text-neutral-600">"{intro}"</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </OrgAppShell>
  );
}
