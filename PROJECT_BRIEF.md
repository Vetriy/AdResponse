# Project Brief

## Thesis topic

Development of an interactive online service for primary response to client requests for an advertising agency.

## Purpose

The system is intended to automate the first response to client messages on an advertising agency website.

The service should:
- receive a client request;
- analyze the text;
- determine the request category;
- detect emotional tone;
- select relevant prepared manager comments;
- generate a primary response using a local LLM through llama.cpp;
- ask clarifying questions if there is not enough information;
- transfer the dialogue to a manager if needed;
- preserve the full dialogue context.

## User roles

1. Client
- sends a message;
- receives an automatic response;
- answers clarifying questions;
- can request a manager.

2. Manager
- sees all client requests;
- opens dialogue history;
- accepts a request;
- sends manual responses;
- changes request status;
- adds prepared comments.

3. Administrator
- manages categories;
- manages prepared comments;
- manages users;
- configures response rules.

## Main entities

- User;
- ClientSession;
- Conversation;
- Message;
- Appeal;
- Category;
- KnowledgeBaseItem;
- SentimentAnalysis;
- GeneratedResponse;
- HandoverRequest.

## Request categories

- service cost;
- advertising campaign launch;
- low number of leads;
- dissatisfaction with campaign results;
- limited budget;
- request for consultation;
- request to contact manager;
- general question;
- other.

## Emotional tones

- neutral;
- interested;
- anxious;
- disappointed;
- irritated;
- negative.

## Key rule

The LLM must not invent business promises, prices, deadlines, guarantees, or facts. It must generate a response based on prepared manager comments and system rules.