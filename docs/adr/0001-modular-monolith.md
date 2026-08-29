# ADR 0001: Django/Wagtail modular monolith

Status: Accepted  
Date: 2026-08-30

## Context

The platform combines relational property inventory, private customer/location data, granular permissions, audit history, inquiry workflows, and editorial publishing. It must remain operable by Lala and maintainable without coordinating multiple independent services.

## Decision

Use Django 6.0, Wagtail 7.4 LTS, and PostgreSQL in a modular monolith. Public pages use server-rendered templates with progressive enhancement. Internal modules own their business rules and communicate through explicit application services rather than direct cross-module shortcuts.

## Consequences

- Authentication, CMS, business data, and public rendering share one deployment and authorization boundary.
- PostgreSQL constraints remain the final line of defense for relational invariants.
- External providers are isolated behind adapters.
- A separate frontend or service may be introduced later only when a measured requirement justifies it.
