import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Input, Label, Textarea } from "@/components/ui/Input";
import { useAppStore } from "@/store/useAppStore";

export function NewJobModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const createJob = useAppStore((s) => s.createJob);
  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("");
  const [location, setLocation] = useState("Remote");
  const [type, setType] = useState("Full-time");
  const [description, setDescription] = useState("");

  const submit = async () => {
    if (!title.trim()) return;
    const job = await createJob({ title, department, location, type, description });
    onClose();
    navigate(`/jobs/${job.id}`);
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Create a new job"
      description="Paste a job description and we'll generate an evaluation rubric automatically."
      width="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={!title.trim()}>
            Create job
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="title">Job title *</Label>
            <Input
              id="title"
              placeholder="e.g. Senior Backend Engineer"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="department">Department</Label>
            <Input
              id="department"
              placeholder="Engineering"
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
            />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="location">Location</Label>
            <Input
              id="location"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="type">Employment type</Label>
            <Input id="type" value={type} onChange={(e) => setType(e.target.value)} />
          </div>
        </div>
        <div>
          <Label htmlFor="description">Job description</Label>
          <Textarea
            id="description"
            rows={6}
            placeholder="Paste the job description here — we'll extract must-have skills and generate a weighted rubric."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
      </div>
    </Modal>
  );
}
