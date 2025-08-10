GRANDMA'S AI ASSISTANT

Question Statement/Production Information: This is backend architecutre for an ai assitant which can do the following things - 
- set up bookings at salons
- set up bookings at retraunts
- remind a user to take medicines
- inform family users about the medicines
- share other kinds of activities. 

This application backend has been created thinking in mind that this would be used by a user who is old, has some cognitive deficiency.

NOTE: This application has been created for a startup with POC level code, has production scaling wherever required. This code is written in a way that it can be scaled up efficiently to a million users. All services can be easily fetched out later on when required. 

Steps for running the server - 

pip install -r requirements.txt
set up the env file (current settings file (core/config) -> is hardcoded with dummy values)

- Run local containers for postgres and redis
docker compose up postgres redis

- Run the app server 
python -m run_server

- Run the worker
python -m worker

LLD Design of the system - 



HLD Design - 
Workers can be run over lambdas or a EC2, depending upon the queue load. Scaling of these workers has been kept independent so that even at POC level we can support a good amount of traffic which gives up time to scale up the service, extract services into separate containers and run them. 



# 👵 Grandma's AI Assistant

**Empowering independence for elderly users and people with cognitive impairments.**

Grandma's AI Assistant is a backend service that helps users perform everyday activities using natural language.  
It is a **POC-quality codebase** designed with **production scaling patterns** so services can be extracted and scaled later to support millions of users.

---

## 🚀 Capabilities

The assistant implements (POC) features for:

- **Restaurant bookings**
- **Salon bookings**
- **Medicine reminders**
- **Family notifications** (e.g., inform family members about medicines)
- **Other daily activities** via natural language

---

## 🛠 Overview

This backend follows a modular, extensible architecture:

- **Intent processing** → (LLM → structured intent)
- **Task routing** → (map intent → service)
- **Task services** → (execute domain logic like booking, reminders)
- **Persistence** → (Postgres)
- **Queueing & workers** → (Redis streams + consumers)
- **Provider layer** → (LLM adapters with schema enforcement and retries)

Although a POC, the design supports **horizontal scaling** and separation of concerns so components can be extracted into microservices when needed.

---

## ✨ Key Features

- **Robust Intent Processing** — Use LLM providers to detect intent and extract parameters, validated against schemas.
- **Service Router** — Dynamically maps intents to service implementations.
- **Task Queue** — Decouples API layer from execution (Redis streams & consumer groups).
- **Worker Processes** — Independent worker pool for executing tasks (can run on containers, EC2, or Lambda).
- **Schema Validation & Retries** — Providers enforce JSON/schema output and have retry/self-correction logic.
- **Observability-ready** — Structured logging and hooks for metrics/alerting.

---

## 📂 System Design

### Low-Level Design (LLD)

- **Providers**: LLM client wrappers (`OpenAIProvider`, etc.) that take prompts + schema and return validated structured output.
- **Intent Processor**: Normalizes LLM output into a `TaskRequest` DTO (intent, details, confidence, etc.).
- **Task Router**: Lookup map that returns the correct `BaseTaskService` for a given intent.
- **Task Services**: Per-intent execution logic (`RestaurantBookingService`, `MedicineReminderService`, ...).
- **Repository Layer**: `TaskRepository`, `UserRepository` for DB operations (async SQLAlchemy).
- **Workers & Consumers**: Read from Redis streams, perform processing, ack/xack, and support retries & dead-lettering.

### High-Level Design (HLD)

- **API Layer** (FastAPI): Receives user requests, calls intent processing, creates task DB entries, enqueues tasks.
- **Queue** (Redis): Streams & consumer groups for reliable distribution and at-least-once semantics.
- **Worker Layer**: Runs `TaskConsumer` instances that call `TaskService.process_task(...)`.
- **DB** (Postgres): Stores users, tasks, task states, results, and auditing fields.

---

## 🏁 Quickstart — Run locally

> Assumes you have **Python**, **Docker**, and **Docker Compose** installed.

1. Install dependencies:
```bash
pip install -r requirements.txt
```
2. Create .env file (or edit core/config for defaults).
3.Start Postgres and Redis:
```bash
docker compose up postgres redis
```
4. Start the API server:
```bash
python -m run_server
```
5. Start the worker:
```bash
python -m worker
```


🧩 Example Request Flow
User says: "Book me a table for 4 at Olive Garden tomorrow 7pm."
FastAPI endpoint receives text and user context.
IntentProcessor calls AI provider with prompt + schema.
LLM returns structured JSON → TaskRequest (intent=restaurant_booking, details=…).
API creates a Task record and enqueues the task to Redis.
Worker reads from Redis, calls TaskService.process_task.
Service routes to RestaurantBookingService, executes booking.
Task status is updated (COMPLETED / FAILED), result saved.
Webhook notification sent.
