"""Generate 10 brand-new sample CV PDFs for manual testing of the PDF upload
flow. These use fresh names/emails/phones so uploading them via
AddCandidateModal never triggers the email-dedupe against the seeded 228.

Usage:
    <venv>/bin/python scripts/synthetic/convert/generate_sample_resumes.py

Writes: sample-resumes/*.pdf
        frontend/public/resumes/samples/*.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

from generate_resume_pdfs import render, PUBLIC_DIR, safe

ROOT = Path(__file__).resolve().parents[3]
SAMPLE_DIR = ROOT / "sample-resumes"
SAMPLE_PUBLIC = PUBLIC_DIR / "samples"

SAMPLES = [
    {
        "id": "sample-backend-go",
        "name": "Priya Natarajan",
        "email": "priya.natarajan.sample@example.com",
        "phone": "(555) 240-8812",
        "location": "Austin, TX",
        "currentTitle": "Senior Backend Engineer",
        "summary": "Backend engineer with 9 years of experience shipping Go and PostgreSQL services on Kubernetes. Designed gRPC APIs and Kafka event pipelines serving 40M requests/day, and led the migration of a monolith to distributed services.",
        "skills": ["Go", "PostgreSQL", "Kubernetes", "gRPC", "Kafka", "Redis", "Docker", "Terraform", "AWS", "System Design"],
        "experience": [
            {"title": "Senior Backend Engineer", "company": "Aurora Pay", "from": "2020-06", "to": None},
            {"title": "Backend Engineer", "company": "Nimbus Analytics", "from": "2016-03", "to": "2020-05"},
        ],
        "education": "B.S. Computer Science, University of Texas at Austin",
        "certifications": "AWS Certified Solutions Architect, CKAD",
    },
    {
        "id": "sample-frontend-react",
        "name": "Marcus Delacroix",
        "email": "marcus.delacroix.sample@example.com",
        "phone": "(555) 733-0914",
        "location": "Seattle, WA",
        "currentTitle": "Senior Frontend Engineer",
        "summary": "Frontend engineer with 7 years building React and TypeScript applications at scale. Lead on design systems, accessibility, and web performance; reduced core Web Vitals by 60% across a 2M-user product.",
        "skills": ["React", "TypeScript", "Next.js", "JavaScript", "CSS", "Tailwind", "Testing", "Web Performance", "Accessibility"],
        "experience": [
            {"title": "Senior Frontend Engineer", "company": "Fenwick Labs", "from": "2019-02", "to": None},
            {"title": "Frontend Engineer", "company": "Brightline", "from": "2016-07", "to": "2019-01"},
        ],
        "education": "B.A. Graphic Design, University of Washington",
        "certifications": "—",
    },
    {
        "id": "sample-data-engineer",
        "name": "Hannah Okafor",
        "email": "hannah.okafor.sample@example.com",
        "phone": "(555) 619-2047",
        "location": "Chicago, IL",
        "currentTitle": "Data Engineer",
        "summary": "Data engineer specializing in Spark and Airflow pipelines over BigQuery and Snowflake. Built real-time streaming jobs with Kafka that cut warehouse load time by 4x and introduced dbt for transformation.",
        "skills": ["Python", "SQL", "Spark", "Airflow", "dbt", "Kafka", "BigQuery", "Snowflake", "AWS", "Data Modeling"],
        "experience": [
            {"title": "Data Engineer", "company": "Meridian Health", "from": "2019-04", "to": None},
            {"title": "Analytics Engineer", "company": "Cartwheel", "from": "2017-01", "to": "2019-03"},
        ],
        "education": "M.S. Information Systems, Northwestern University",
        "certifications": "Google Cloud Professional Data Engineer",
    },
    {
        "id": "sample-ml-llm",
        "name": "Andrés Villanueva",
        "email": "andres.villanueva.sample@example.com",
        "phone": "(555) 402-7730",
        "location": "San Diego, CA",
        "currentTitle": "ML Engineer",
        "summary": "Machine learning engineer with 6 years of experience training and serving LLMs and transformer models in production. Built RAG systems on vector databases and cut inference latency 45% with optimized serving.",
        "skills": ["Python", "PyTorch", "TensorFlow", "LLM", "RAG", "LangChain", "Vector DB", "MLOps", "Docker", "AWS"],
        "experience": [
            {"title": "ML Engineer", "company": "VectorMind AI", "from": "2020-08", "to": None},
            {"title": "Data Scientist", "company": "Helix Analytics", "from": "2017-09", "to": "2020-07"},
        ],
        "education": "M.S. Machine Learning, Georgia Institute of Technology",
        "certifications": "—",
    },
    {
        "id": "sample-devops-sre",
        "name": "Sofia Lindqvist",
        "email": "sofia.lindqvist.sample@example.com",
        "phone": "(555) 318-5564",
        "location": "Denver, CO",
        "currentTitle": "DevOps Engineer",
        "summary": "DevOps and SRE engineer with 8 years operating Kubernetes clusters and CI/CD at scale. Introduced GitOps with ArgoCD, drove SLO-based alerting, and improved on-call reliability with Terraform-managed infrastructure.",
        "skills": ["Kubernetes", "Docker", "Terraform", "Ansible", "AWS", "CI/CD", "GitLab", "Monitoring", "Linux", "Bash"],
        "experience": [
            {"title": "DevOps Engineer", "company": "Northwind Cloud", "from": "2018-11", "to": None},
            {"title": "Site Reliability Engineer", "company": "Datapoint Systems", "from": "2015-05", "to": "2018-10"},
        ],
        "education": "B.S. Computer Engineering, University of Colorado Boulder",
        "certifications": "CKA, AWS Certified DevOps Engineer",
    },
    {
        "id": "sample-mobile-ios",
        "name": "Kelechi Obi",
        "email": "kelechi.obi.sample@example.com",
        "phone": "(555) 884-3091",
        "location": "New York, NY",
        "currentTitle": "iOS Engineer",
        "summary": "iOS engineer with 6 years of Swift and SwiftUI experience shipping consumer apps used by millions. Owned offline-first sync, push notifications, and CI/CD for App Store releases.",
        "skills": ["Swift", "SwiftUI", "iOS", "Combine", "Core Data", "REST APIs", "Git", "CI/CD", "Testing"],
        "experience": [
            {"title": "iOS Engineer", "company": "Pocketline", "from": "2019-06", "to": None},
            {"title": "Mobile Engineer", "company": "Grove Studio", "from": "2016-08", "to": "2019-05"},
        ],
        "education": "B.S. Computer Science, Columbia University",
        "certifications": "—",
    },
    {
        "id": "sample-security",
        "name": "Yuki Tanaka",
        "email": "yuki.tanaka.sample@example.com",
        "phone": "(555) 275-6408",
        "location": "Portland, OR",
        "currentTitle": "Security Engineer",
        "summary": "Application security engineer with 7 years hardening cloud workloads and code. Built SAST/DAST pipelines into CI, led bug-bounty triage, and achieved SOC 2 Type II readiness.",
        "skills": ["Security", "Application Security", "Penetration Testing", "OWASP", "AWS", "Docker", "Kubernetes", "Linux", "Python"],
        "experience": [
            {"title": "Security Engineer", "company": "IronGate", "from": "2019-03", "to": None},
            {"title": "Security Analyst", "company": "Trustline", "from": "2015-09", "to": "2019-02"},
        ],
        "education": "B.S. Cyber Security, Oregon State University",
        "certifications": "CISSP, AWS Certified Security",
    },
    {
        "id": "sample-qa-sdet",
        "name": "Olivia Novak",
        "email": "olivia.novak.sample@example.com",
        "phone": "(555) 590-1173",
        "location": "Phoenix, AZ",
        "currentTitle": "SDET",
        "summary": "SDET with 6 years automating web and API test suites in CI/CD. Built a Playwright and Cypress framework that cut regression time by 70% and integrated contract testing with Pact.",
        "skills": ["Testing", "Automation", "Playwright", "Cypress", "Selenium", "JavaScript", "Python", "REST APIs", "CI/CD", "Git"],
        "experience": [
            {"title": "SDET", "company": "QualityStack", "from": "2018-02", "to": None},
            {"title": "QA Engineer", "company": "Everbright", "from": "2015-07", "to": "2018-01"},
        ],
        "education": "B.S. Software Engineering, Arizona State University",
        "certifications": "ISTQB Certified Tester",
    },
    {
        "id": "sample-java-microservices",
        "name": "Rahul Mehta",
        "email": "rahul.mehta.sample@example.com",
        "phone": "(555) 466-2205",
        "location": "Jersey City, NJ",
        "currentTitle": "Java Microservices Engineer",
        "summary": "Backend engineer with 8 years building Java Spring Boot microservices on AWS. Led a service-mesh migration to Kubernetes and improved transaction throughput 3x with event-driven design.",
        "skills": ["Java", "Spring Boot", "Microservices", "Kubernetes", "AWS", "Kafka", "PostgreSQL", "Docker", "REST APIs"],
        "experience": [
            {"title": "Senior Java Engineer", "company": "Bridgewater Financial", "from": "2019-01", "to": None},
            {"title": "Java Developer", "company": "Ledgerly", "from": "2015-06", "to": "2018-12"},
        ],
        "education": "M.S. Computer Science, Rutgers University",
        "certifications": "Oracle Certified Professional Java SE",
    },
    {
        "id": "sample-solutions-architect",
        "name": "Elena Petrova",
        "email": "elena.petrova.sample@example.com",
        "phone": "(555) 341-8829",
        "location": "Atlanta, GA",
        "currentTitle": "Solutions Architect",
        "summary": "Solutions architect with 10 years across cloud architecture, distributed systems, and client-facing design. Owned AWS landing zones and reference architectures adopted across 12 product teams.",
        "skills": ["AWS", "Architecture", "System Design", "Kubernetes", "Terraform", "Cloud", "Microservices", "Networking", "Cost Optimization"],
        "experience": [
            {"title": "Solutions Architect", "company": "CloudBridge", "from": "2018-05", "to": None},
            {"title": "Systems Architect", "company": "Meridian Telecom", "from": "2012-09", "to": "2018-04"},
        ],
        "education": "B.S. Computer Science, Georgia Tech",
        "certifications": "AWS Certified Solutions Architect Professional, CKA",
    },
]


def main() -> int:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLE_PUBLIC.mkdir(parents=True, exist_ok=True)
    for p in SAMPLES:
        pdf = render(p)
        pdf.output(str(SAMPLE_DIR / f"{p['id']}.pdf"))
        pdf.output(str(SAMPLE_PUBLIC / f"{p['id']}.pdf"))
    print(f"Wrote {len(SAMPLES)} sample CV PDFs -> {SAMPLE_DIR} and {SAMPLE_PUBLIC}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
