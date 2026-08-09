import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { Input, Label } from "@/components/ui/Input";

export function LoginCandidate() {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50 px-6">
      <div className="w-full max-w-sm rounded-lg border border-neutral-200 bg-white p-8 shadow-sm">
        <div className="mb-6 flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-brand-primary text-sm font-bold text-white">
            A
          </div>
          <span className="text-[15px] font-semibold text-neutral-900">Statnativ</span>
        </div>

        <h2 className="text-xl font-semibold text-neutral-900">Welcome back</h2>
        <p className="mt-1 text-sm text-neutral-500">
          Sign in to continue your interview process.
        </p>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            navigate("/candidate");
          }}
          className="mt-6 space-y-4"
        >
          <div>
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" defaultValue="sophia.martinez@gmail.com" />
          </div>
          <div>
            <Label htmlFor="password">Password</Label>
            <Input id="password" type="password" defaultValue="••••••••" />
          </div>
          <Button type="submit" className="w-full" size="lg">
            Sign in
          </Button>
        </form>

        <div className="my-5 flex items-center gap-3">
          <div className="h-px flex-1 bg-neutral-200" />
          <span className="text-xs text-neutral-400">or continue with</span>
          <div className="h-px flex-1 bg-neutral-200" />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Button type="button" variant="secondary">Google</Button>
          <Button type="button" variant="secondary">LinkedIn</Button>
        </div>

        <p className="mt-5 text-center text-sm text-neutral-500">
          Hiring for your team?{" "}
          <button
            onClick={() => navigate("/login")}
            className="font-medium text-brand-primary hover:underline"
          >
            Organization sign in
          </button>
        </p>
      </div>
    </div>
  );
}
