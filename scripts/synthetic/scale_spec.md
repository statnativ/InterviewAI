# Scale Spec — 37 jobs / 9 IT domains / 90 people / ~195 applications

Human-authored constants for the full build. The pilot's 3 jobs (job-001..003) and 15 people
(person-001..015) are **kept as-is**; this spec adds 34 jobs and 75 people. Naming per
`pilot_spec.md`. `name(level, weight)` — weights per job sum to 100.

## backend (6 jobs; job-001 exists)

| id | title | seniority | years | requiredSkills |
|---|---|---|---|---|
| job-001-senior-backend-go *(exists)* | Senior Backend Engineer (Go) | Senior | 5 | Go(must,20) PostgreSQL(must,15) Kubernetes(must,15) gRPC(must,15) System Design(must,10) Kafka(nice,10) Terraform(nice,5) Redis(nice,5) Observability(nice,5) |
| job-004-staff-backend-go | Staff Backend Engineer (Go) | Staff | 8 | Go(must,25) Distributed Systems(must,15) Kubernetes(must,15) PostgreSQL(must,10) System Design(must,10) gRPC(nice,10) Kafka(nice,5) Terraform(nice,5) Observability(nice,5) |
| job-005-backend-python | Backend Engineer (Python) | Mid | 3 | Python(must,25) FastAPI(must,15) PostgreSQL(must,15) Redis(must,10) Docker(must,10) Django(nice,10) Celery(nice,5) AWS(nice,5) SQLAlchemy(nice,5) |
| job-006-java-microservices | Java Microservices Engineer | Senior | 5 | Java(must,25) Spring Boot(must,20) Kafka(must,15) PostgreSQL(must,10) Docker(must,10) Kubernetes(nice,10) AWS(nice,5) SQL(nice,5) |
| job-007-node-backend | Node.js Backend Engineer | Mid | 3 | Node.js(must,25) TypeScript(must,15) PostgreSQL(must,15) REST APIs(must,10) Redis(must,10) GraphQL(nice,10) Docker(nice,10) AWS(nice,5) |
| job-008-dotnet-backend | .NET Backend Engineer | Mid | 3 | C#(must,25) ASP.NET Core(must,20) SQL Server(must,15) Azure(must,10) REST APIs(must,10) Kubernetes(nice,10) Docker(nice,5) EF Core(nice,5) |

## frontend (4 jobs; job-002 exists)

| id | title | seniority | years | requiredSkills |
|---|---|---|---|---|
| job-002-senior-frontend-react *(exists)* | Senior Frontend Engineer (React) | Senior | 5 | React(must,20) TypeScript(must,20) CSS & Design Systems(must,15) Testing (Jest / React Testing Library)(must,10) Frontend Performance(must,10) Next.js(nice,10) GraphQL(nice,5) Accessibility (a11y)(nice,5) Storybook(nice,5) |
| job-009-frontend-angular | Frontend Engineer (Angular) | Mid | 3 | Angular(must,25) TypeScript(must,20) RxJS(must,15) HTML5 & CSS(must,10) Testing (Jasmine / Karma)(must,10) NgRx(nice,10) Accessibility (a11y)(nice,5) CI/CD(nice,5) |
| job-010-frontend-vue | Vue.js Engineer | Mid | 3 | Vue.js(must,25) TypeScript(must,20) Pinia / Vuex(must,15) HTML5 & CSS(must,10) Testing (Vitest)(must,10) Nuxt(nice,10) Accessibility (a11y)(nice,5) Storybook(nice,5) |
| job-011-frontend-platform | Frontend Platform Engineer | Staff | 8 | TypeScript(must,20) React(must,15) Build Tooling (Vite / Webpack)(must,15) CI/CD(must,15) Frontend Performance(must,10) Monorepos (Turborepo)(nice,10) GraphQL(nice,5) Design Systems(nice,5) Testing (Jest / React Testing Library)(nice,5) |

## mobile (3 jobs)

| id | title | seniority | years | requiredSkills |
|---|---|---|---|---|
| job-012-ios-engineer | iOS Engineer | Mid | 3 | Swift(must,25) SwiftUI(must,20) UIKit(must,15) Xcode & iOS Tooling(must,10) App Architecture (MVVM)(must,10) Combine(nice,10) Core Data(nice,5) CI/CD (Fastlane)(nice,5) |
| job-013-android-engineer | Android Engineer | Mid | 3 | Kotlin(must,25) Jetpack Compose(must,20) Android SDK(must,15) Coroutines(must,10) MVVM(must,10) Room(nice,10) Retrofit(nice,5) Firebase(nice,5) |
| job-014-react-native | React Native Engineer | Mid | 3 | React Native(must,25) TypeScript(must,20) JavaScript(must,15) Native Modules(must,10) State Management (Redux / Zustand)(must,10) Expo(nice,10) Testing (Detox)(nice,5) CI/CD(nice,5) |

## data (5 jobs; job-003 exists)

| id | title | seniority | years | requiredSkills |
|---|---|---|---|---|
| job-003-data-engineer *(exists)* | Data Engineer | Mid | 3 | SQL(must,20) Python(must,15) Apache Spark(must,15) Data Modeling(must,10) Airflow(must,10) dbt(nice,10) BigQuery(nice,5) Kafka(nice,5) Terraform(nice,5) Kubernetes(nice,5) |
| job-015-data-analyst | Data Analyst | Junior | 2 | SQL(must,25) Data Visualization (Looker / Tableau)(must,20) Excel(must,15) Statistics(must,10) Python(must,10) dbt(nice,10) Airflow(nice,5) Google Analytics(nice,5) |
| job-016-data-scientist | Data Scientist | Senior | 4 | Python(must,25) Machine Learning(must,20) Statistics(must,15) Pandas(must,10) SQL(must,10) Scikit-learn(nice,10) Deep Learning(nice,5) Experimentation (A/B Testing)(nice,5) |
| job-017-ml-engineer | Machine Learning Engineer | Senior | 4 | Python(must,25) PyTorch(must,20) ML Ops (MLflow)(must,15) Docker(must,10) Kubernetes(must,10) TensorFlow(nice,10) Feature Stores(nice,5) Airflow(nice,5) |
| job-018-ml-platform | ML Platform Engineer | Staff | 6 | Kubernetes(must,20) Python(must,20) MLflow(must,15) CI/CD(must,15) Docker(must,10) Terraform(nice,10) Kubeflow(nice,5) Airflow(nice,5) |

## infra (5 jobs)

| id | title | seniority | years | requiredSkills |
|---|---|---|---|---|
| job-019-devops-engineer | DevOps Engineer | Mid | 3 | Docker(must,25) Kubernetes(must,20) CI/CD (GitHub Actions)(must,15) Terraform(must,15) Linux(must,10) AWS(nice,10) Helm(nice,5) |
| job-020-sre | Site Reliability Engineer | Senior | 5 | Linux(must,20) Kubernetes(must,20) Observability (Prometheus / Grafana)(must,15) Incident Management(must,15) Python(must,10) Terraform(nice,10) Go(nice,5) Service Mesh(nice,5) |
| job-021-platform-engineer | Platform Engineer | Senior | 5 | Kubernetes(must,25) Terraform(must,20) Go(must,15) Cloud Networking(must,10) CI/CD(must,10) ArgoCD(nice,10) Observability(nice,5) Helm(nice,5) |
| job-022-cloud-engineer-aws | Cloud Engineer (AWS) | Mid | 3 | AWS(must,20) Terraform(must,15) Linux(must,15) Networking(must,10) Python(nice,10) Docker(nice,10) Kubernetes(nice,10) Cloud Security(nice,10) |
| job-023-db-reliability | Database Reliability Engineer | Senior | 5 | PostgreSQL(must,25) Performance Tuning(must,20) Replication & HA(must,15) Linux(must,10) SQL(must,10) Kubernetes(nice,10) Cloud Databases(nice,5) Python(nice,5) |

## security (4 jobs)

| id | title | seniority | years | requiredSkills |
|---|---|---|---|---|
| job-024-security-engineer | Security Engineer | Mid | 3 | Application Security(must,20) Network Security(must,15) Linux(must,15) Penetration Testing(must,15) Python(must,10) SIEM(nice,10) Cloud Security(nice,10) OWASP(nice,5) |
| job-025-appsec | Application Security Engineer | Senior | 4 | OWASP Top 10(must,25) Threat Modeling(must,20) Secure Code Review(must,15) Web Technologies(must,10) SAST / DAST(must,10) Python(nice,10) Kubernetes Security(nice,5) CI/CD Security(nice,5) |
| job-026-cloud-security | Cloud Security Engineer | Senior | 4 | AWS Security(must,25) IAM & Identity(must,20) Terraform(must,15) Compliance (SOC2)(must,10) Cloud Networking(must,10) Kubernetes Security(nice,10) Python(nice,5) SIEM(nice,5) |
| job-027-soc-analyst | SOC Analyst | Junior | 1 | SIEM(must,25) Incident Response(must,20) Network Fundamentals(must,15) Log Analysis(must,15) Threat Intelligence(must,10) Endpoint Detection(nice,10) Scripting (Python)(nice,5) |

## qa (2 jobs)

| id | title | seniority | years | requiredSkills |
|---|---|---|---|---|
| job-028-sdet | SDET | Mid | 3 | Test Automation(must,25) Python(must,20) Selenium / Playwright(must,20) CI/CD(must,10) API Testing(must,10) Java(nice,10) Performance Testing(nice,5) |
| job-029-qa-automation | QA Automation Engineer | Mid | 3 | Selenium(must,25) JavaScript(must,20) Test Automation(must,20) API Testing(must,10) CI/CD(must,10) Cypress(nice,10) Jira / TestRail(nice,5) |

## architecture (4 jobs)

| id | title | seniority | years | requiredSkills |
|---|---|---|---|---|
| job-030-solutions-architect | Solutions Architect | Senior | 7 | Cloud Architecture (AWS / Azure)(must,25) System Design(must,20) Microservices(must,15) Enterprise Integration(must,10) Cost Optimization(must,10) Containerization(nice,10) Security Architecture(nice,5) Migration Strategies(nice,5) |
| job-031-systems-architect | Systems Architect | Staff | 8 | Distributed Systems(must,25) System Design(must,20) Database Design(must,15) Scalability(must,15) Security(must,10) Event-Driven Architecture(nice,10) Cloud Platforms(nice,5) |
| job-032-staff-distributed | Staff Engineer (Distributed Systems) | Staff | 8 | Distributed Systems(must,25) System Design(must,20) Go(must,15) PostgreSQL(must,10) Scalability(must,10) Kafka(nice,10) Kubernetes(nice,5) Observability(nice,5) |
| job-033-engineering-manager | Engineering Manager | Senior | 6 | Team Leadership(must,25) Technical Mentorship(must,20) Agile Delivery(must,15) Performance Management(must,10) Stakeholder Communication(must,10) Software Architecture(nice,10) Hiring & Onboarding(nice,5) Metrics & KPIs(nice,5) |

## ai (4 jobs)

| id | title | seniority | years | requiredSkills |
|---|---|---|---|---|
| job-034-llm-engineer | LLM / GenAI Engineer | Senior | 4 | Python(must,25) LLM APIs (OpenAI / Anthropic)(must,20) Prompt Engineering(must,15) RAG Patterns(must,15) Vector Databases(must,10) LangChain(nice,10) Fine-Tuning(nice,5) |
| job-035-genai-app-dev | GenAI Application Developer | Mid | 3 | Python(must,25) LLM APIs (OpenAI / Anthropic)(must,20) React(must,15) FastAPI(must,10) RAG Patterns(must,10) Docker(nice,10) LangChain(nice,5) Prompt Engineering(nice,5) |
| job-036-cv-engineer | Computer Vision Engineer | Senior | 4 | Python(must,25) PyTorch(must,20) OpenCV(must,15) Deep Learning(must,15) Image Processing(must,10) TensorFlow(nice,10) Docker(nice,5) |
| job-037-rag-engineer | RAG / Information Retrieval Engineer | Senior | 4 | Python(must,25) Vector Databases(must,20) Embeddings(must,15) RAG Patterns(must,15) NLP(must,10) LangChain(nice,10) Elasticsearch(nice,5) |

## People pools (90 total; person-001..015 exist from pilot)

New pools per domain — read the domain's job files for exact skill spellings. Pool members
each apply to ~2 jobs in-domain (+ a few cross-domain). Spread per job preserved: each job's
applicants must include ≥1 STRONG (all must-haves), ≥1 weak/mid (missing ≥1 must-have).

**backend +9 (person-016..024):** Lena Fischer (Python, 5y, STRONG), Omar Haddad (Python, 3y, MID→data), Vikram Singh (Java, 6y, STRONG), Nina Kowalski (Java, 3y, MID), David Osei (Node, 5y, STRONG), Chloe Dubois (Node, 2y, MID), Tom Becker (.NET, 5y, STRONG), Anika Sharma (C#, 2y, WEAK), Mateo Alvarez (Staff Go, 10y, STRONG→architecture)

**frontend +5 (person-025..029):** Zoe Bennett (Angular, 4y, STRONG), Ryan Clark (Angular, 2y, MID), Amelie Laurent (Vue, 4y, STRONG), Daniel Kim (Vue, 2y, MID), Freya Nielsen (Frontend Platform, 7y, STRONG)

**data +7 (person-030..036):** Aisha Khan (Analyst, 3y, STRONG), Ben Carter (Analyst, 1y, WEAK), Maria Lopez (Data Scientist, 5y, STRONG), Kenji Watanabe (DS, 3y, MID), Olga Ivanova (ML Eng, 5y, STRONG), Sam Thompson (ML Platform, 7y, STRONG), Nina Rossi (Python ML, 3y, MID)

**mobile +8 (person-037..044):** Isaac Cohen (iOS, 4y, STRONG), Lucia Fernández (iOS, 2y, MID), Arjun Mehta (Android, 4y, STRONG), Emily Zhang (Android, 2y, MID), Felix Braun (RN, 4y, STRONG), Sara Haddad (RN, 2y, MID), Oliver Schmidt (mobile gen, 6y, MID), Mia Johansson (iOS jr, 1y, WEAK)

**infra +12 (person-045..056):** Ethan Wood (DevOps, 4y, STRONG), Grace Liu (DevOps, 2y, MID), Noah Green (SRE, 6y, STRONG), Ava Martin (SRE, 3y, MID), Lucas Silva (Platform, 6y, STRONG), Mia Chen (Platform, 3y, MID), Jack Wilson (AWS, 4y, STRONG), Aria Patel (AWS, 2y, MID), Leo Andersson (DB Rel, 6y, STRONG), Ruby Foster (DB Rel, 3y, MID), Max Keller (infra gen, 8y, MID), Zoe Laurent (cloud jr, 1y, WEAK)

**security +9 (person-057..065):** Adam Scott (Sec, 4y, STRONG), Layla Ahmed (Sec, 2y, MID), Victor Ivanov (AppSec, 5y, STRONG), Nia Edwards (AppSec, 3y, MID), Omar Farooq (CloudSec, 5y, STRONG), Julia Novak (CloudSec, 3y, MID), Evan Brooks (SOC, 2y, STRONG-ish), Chloe Adams (SOC, 1y, MID), Marcus Reed (SOC jr, 1y, WEAK)

**qa +6 (person-066..071):** Hannah Cole (SDET, 4y, STRONG), Josh Park (SDET, 2y, MID), Isabel Gomez (QA Auto, 4y, STRONG), Tyler Nguyen (QA Auto, 2y, MID), Anna Kovács (QA, 3y, MID), Liam Walsh (QA jr, 1y, WEAK)

**architecture +10 (person-072..081):** Robert Hayes (SolArch, 9y, STRONG), Priya Rao (SolArch, 5y, MID), James Carter (SysArch, 10y, STRONG), Sofia Novak (SysArch, 6y, MID), Daniel Wright (Staff Dist, 10y, STRONG), Emma Turner (Staff Dist, 6y, MID), Michael Brown (EM, 8y, STRONG), Sarah Kim (EM, 5y, MID), Alex Morgan (arch gen, 8y, MID), Chris Evans (arch jr, 3y, WEAK)

**ai +9 (person-082..090):** Yasmine Benali (LLM, 5y, STRONG), Kwame Mensah (LLM, 3y, MID), Charlotte Dubois (GenAI App, 4y, STRONG), Ethan Ross (GenAI App, 2y, MID), Wei Liu (CV, 6y, STRONG), Maya Kapoor (CV, 4y, MID), Liam Harris (RAG, 5y, STRONG), Zara Ali (RAG, 3y, MID), Henry Ford (AI gen, 6y, MID)

## Cross-domain applications (explicit; exercised in the join script)

person-003→job-003 *(exists)* · person-005→job-022 · person-016→job-003 · person-017→job-015 ·
person-024→job-032 · person-029→job-035 · person-082→job-017 · person-049→job-018 ·
person-018→job-028 · person-084→job-005
