# Admin Dashboard

This is the management interface for the Medical Chatbot platform.

## Features
- **Project Onboarding:** Register new projects with metadata (owner, contact, audiences).
- **Knowledge Pipeline:** Upload PDF/Markdown sources and monitor background processing.
- **Activation Gate:** Trigger indexing with automated retrieval verification.
- **RBAC:** Scoped access for Super Admins and Project Admins.
- **Monitoring:** Platform-wide stats and audit logs.

## How to Run

1. Ensure the backend API is running on `http://localhost:8000`.
2. Navigate to this directory:
   ```bash
   cd interfaces/admin-dashboard
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
4. Open your browser to the URL shown (usually `http://localhost:3000`).

## Testing the Pipeline

1. **Login:** Use the bootstrap admin credentials (from your `.env` or project settings).
2. **Onboard:** Create a new project (e.g., `maternal_health`).
3. **Upload:** Go to the Knowledge Base for the project, upload a PDF.
4. **Monitor:** Wait for the status to show "Pending Review".
5. **Activate:** Click "Activate" to trigger the indexing run.
6. **Verify:** Check the alert for the retrieval verification result.
