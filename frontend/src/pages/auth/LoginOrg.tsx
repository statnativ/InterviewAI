import { useNavigate } from "react-router-dom";
import { Check } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input, Label } from "@/components/ui/Input";

export function LoginOrg() {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen">
      <div className="relative hidden w-[45%] flex-col justify-between overflow-hidden bg-neutral-900 px-12 py-12 text-white lg:flex">
        <div className="pointer-events-none absolute -top-24 -right-24 h-72 w-72 rounded-full bg-brand-primary/20" />
        <div className="pointer-events-none absolute -bottom-32 -left-16 h-72 w-72 rounded-full bg-brand-primary/10" />

        <div className="relative flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-brand-primary text-sm font-bold">
            A
          </div>
          <span className="text-[15px] font-semibold">Statnativ</span>
        </div>

        <div className="relative">
          <h1 className="text-4xl font-bold leading-tight">
            Hire smarter, not harder.
          </h1>
          <p className="mt-4 max-w-sm text-neutral-300">
            AI-powered interviews and structured, evidence-based evaluation
            for modern hiring teams.
          </p>
          <ul className="mt-8 space-y-3">
            {[
              "AI-generated rubrics from any job description",
              "Structured, evidence-backed candidate scoring",
              "End-to-end pipeline — screen, interview, compare",
            ].map((item) => (
              <li key={item} className="flex items-center gap-3 text-sm">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-primary">
                  <Check className="h-3 w-3" />
                </span>
                {item}
              </li>
            ))}
          </ul>
        </div>

        <div />
      </div>

      <div className="relative flex flex-1 items-center justify-center px-6">
        <div className="absolute top-6 right-8 text-sm text-neutral-500">
          Interviewing as a candidate?{" "}
          <button
            onClick={() => navigate("/candidate/login")}
            className="font-medium text-brand-primary hover:underline"
          >
            Candidate sign in →
          </button>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            navigate("/dashboard");
          }}
          className="w-full max-w-sm"
        >
          <h2 className="text-2xl font-semibold text-neutral-900">
            Sign in to your organization
          </h2>
          <p className="mt-1 text-sm text-neutral-500">
            Manage jobs, candidates, and interviews for your team.
          </p>

          <div className="mt-6">
            <Label htmlFor="email">Work email</Label>
            <Input id="email" type="email" placeholder="you@company.com" defaultValue="riley@northwindhealth.com" />
          </div>
          <div className="mt-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="password">Password</Label>
              <a href="#" className="text-xs font-medium text-brand-primary hover:underline">
                Forgot password?
              </a>
            </div>
            <Input id="password" type="password" defaultValue="••••••••" />
          </div>

          <Button type="submit" className="mt-6 w-full" size="lg">
            Sign in
          </Button>

          <div className="my-5 flex items-center gap-3">
            <div className="h-px flex-1 bg-neutral-200" />
            <span className="text-xs text-neutral-400">or continue with</span>
            <div className="h-px flex-1 bg-neutral-200" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Button type="button" variant="secondary">Google</Button>
            <Button type="button" variant="secondary">Microsoft</Button>
          </div>

          <p className="mt-5 text-center text-sm text-neutral-500">
            Don't have an organization account?{" "}
            <a href="#" className="font-medium text-brand-primary hover:underline">
              Get started
            </a>
          </p>
        </form>
      </div>
    </div>
  );
}
