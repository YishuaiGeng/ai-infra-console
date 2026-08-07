# Contributing to AI Infra Console

Thank you for helping improve AI Infra Console. The project is currently in the UI Foundation phase, so changes should preserve the phase boundaries described in the development roadmap.

## Development setup

Requirements:

- Node.js 20.9 or newer
- npm 10 or newer

Install and start the web console from the repository root:

```bash
npm install
npm run dev
```

Before opening a pull request, run:

```bash
npm run check
```

## Change guidelines

- Keep infrastructure, GPU, model, and deployment data internally consistent.
- Put reusable primitives in `apps/web/src/components/ui` and domain components in their matching component directory.
- Do not add arbitrary remote shell or command execution features.
- Do not commit credentials, private host information, model tokens, or local server records.
- Do not start work from a later roadmap phase unless the previous phase has passed review.
- Keep pull requests focused and include screenshots for visible UI changes.

## Pull requests

Describe the user-facing change, implementation scope, verification commands, and any remaining limitations. Link an issue when one exists.
