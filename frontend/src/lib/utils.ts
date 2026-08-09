import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { OrgRole } from "@/data/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Mirrors app/services/authz.py's WRITE_ROLES: cosmetic gate only — the
 * server's require_roles dependency is the real enforcement boundary. Hiding
 * a button a hiring manager can't use avoids a round-trip just to hit a 403. */
export function canWrite(role: OrgRole) {
  return role === "admin" || role === "recruiter";
}

export function initials(name: string) {
  return name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function formatRelativeTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
