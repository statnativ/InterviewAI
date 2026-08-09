import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { Input, Label } from "@/components/ui/Input";
import { adminApi } from "@/lib/adminApi";

export function AdminLogin() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await adminApi.login(username, password);
      navigate("/admin/tenants", { replace: true });
    } catch {
      setError("Incorrect username or password.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-900 px-6">
      <form onSubmit={handleSubmit} className="w-full max-w-sm rounded-lg bg-white p-8 shadow-xl">
        <div className="mb-6 flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-neutral-900 text-sm font-bold text-white">
            A
          </div>
          <span className="text-[15px] font-semibold text-neutral-900">Platform Admin</span>
        </div>

        <h2 className="text-xl font-semibold text-neutral-900">Sign in</h2>
        <p className="mt-1 text-sm text-neutral-500">
          Master admin access — manage tenants, users, and practice tests.
        </p>

        <div className="mt-6">
          <Label htmlFor="username">Username</Label>
          <Input
            id="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
        </div>
        <div className="mt-4">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </div>

        {error && <p className="mt-3 text-sm text-status-weak-text">{error}</p>}

        <Button type="submit" className="mt-6 w-full" size="lg" disabled={submitting}>
          {submitting ? "Signing in…" : "Sign in"}
        </Button>
      </form>
    </div>
  );
}
