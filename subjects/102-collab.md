@title Multi-User Collaboration — Design Spec
@argument
Design specification for the first multi-user collaboration features in Gossamer: invitation, roles, pending edits, and notification.
@status proto
@pub-time 2026-05-02T00:00Z
@category zzz-debug
@related 100, 101

## Overview

Allow one user (the owner) to invite others to share and collaborate on a project. This spec covers the MVP: roles, project/user data model, pending edit review, agent behavior, and summarization. The invitation flow and notification system are deferred — initial user/project mapping is done manually via an admin screen.

## Roles

Three roles, in order of privilege:

- **Owner.** Full control. Can accept or decline edits, make direct changes. One per project (for now).
- **Contributor.** Can participate in chat, ask the agent to propose edits. Cannot accept or decline edits — proposals go to the owner for review.
- **Observer.** Can see the chat and browse the project. Cannot speak in chat (no text input window shown). Cannot propose edits.

## Data model

Two JSON files serve as a minimal database. Both live in the root of shared data and will eventually be replaced by a single SQLite database.

### projects.json

```json
[
  {
    "id": "SeedPods",
    "name": "SeedPods",
    "members": [
      { "userId": "FA2ABF2F-24EF-40A0-8D65-A0A4FFA3E4E3", "role": "owner" }
    ]
  }
]
```

Each project has an `id`, a display `name`, and a `members` array of `{ userId, role }` pairs. `userId` is currently a username; it will migrate to an opaque ID in a later pass. Roles are `owner`, `contributor`, or `observer`.

### users.json

A user registry. No project membership — that lives in `projects.json`.

The `id` field is currently a UUID token that doubles as a shared secret (future passkey). It will eventually become an opaque ID separate from authentication.

```json
[
  {
    "id": "FA2ABF2F-24EF-40A0-8D65-A0A4FFA3E4E3",
    "name": "Darakshan",
    "initials": "darak",
    "devices": [
      "F86E0D90-9B7A-4EDF-BCC0-70F721D036D9",
      "5E2DCE06-6BD4-4669-A4D9-177DEC7F31C7"
    ],
    "profile": "73 years old, experienced software architect, student of spiritual traditions and philosophy, founder of SeedPods"
  }
]
```

### Admin screen

A page in the admin interface allows the owner to:

- Add a user to a project with a role (by selecting from known users).
- Change a user's role.
- Remove a user from a project.

This replaces the full invitation flow for now. No notification badges, no accept/decline dialogue.

### Migration

The current `config/users.json` inside each project directory is retired. Its data moves to the server-level `users.json` and `projects.json`. The per-project file can remain as a read-only cache if needed for offline use, but the server-level files are authoritative.

## Project switching

Once a user has access to more than one project, they need a way to switch. Switching changes both the chat pane and the browse pane. The UI for this is TBD but could be a project selector in the settings pane or a swipe gesture.

## Pending edits

When a contributor asks the agent to make a change, the agent proposes the edit as a chip. But only the owner can accept or decline it.

- The chip enters a **pending** state. The conversation continues — it does not block.
- The contributor sees their proposal marked "waiting for owner."
- The agent knows the proposal is pending and does not treat it as applied.
- The owner can review pending edits in the browse pane. The proposed change appears as a highlighted diff overlay on the rendered subject, with accept/decline buttons in context.
- A **"next pending"** button on the chip lets the owner cycle through all pending edits.
- This is analogous to document review in Word or Google Docs, except the owner sees the change as a reader would, not as raw markup.

## Agent behavior in multi-user chat

- The agent can see all participants and their roles.
- **Subject detection:** The agent watches the conversation and matches it against subject arguments. When confident, it surfaces a relevant subject via the status line.
- **Hand-raising:** The agent can signal it has something to contribute via the status line, without interrupting.
- **Status line:** A single line the agent can write to at any time — subject detection, hand-raising, pending-edit count, reactions, emoji. Participants can react with emoji back.
- **Mute modes:** The group can toggle between lightweight mode (subject detection only) and full mode (agent follows conversation and can contribute). Muting saves cost.
- The group trains the agent over time. Ignored contributions are signal.

## Minutes (server-triggered summarization)

The server runs a configurable timer (default 30 minutes) after the last message in any user's current chat. When it fires, the server sends the agent a message asking it to summarize the conversation as a summary chip.

The summary captures three things:

- **What was established.** Things the group now holds that they didn't before.
- **What's open.** Things raised but not resolved.
- **What's next.** Anything anyone committed to doing.

These categories are domain-agnostic. The same mechanism fires when context is getting full. One feature, two triggers, same output. The summary is stored as a chip and persists across sessions.

## Notification system (deferred)

The full notification system is deferred to a later phase. It would include:

- Red dot on the lozenge for pending invitations and unread items.
- App badge when any notification is active.
- Settings sidebar highlighting the section wanting attention.
- Lozenge hides when keyboard is active, reappears when keyboard dismisses.
- Invitation flow: owner provides email, invitee gets badge, accept/decline/cancel dialogue.

## Open questions

- What happens to a contributor's pending edits if they are removed from the project?
- How does the "next pending" button order the edits — chronological, by subject, by contributor?
- Should the agent carry context from previous group sessions via stored minutes, or start fresh each time?
- Can there be multiple owners?
