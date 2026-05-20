# NotesFlare — Testing Guide 🧪

Welcome to the NotesFlare testing handbook. This guide explains in simple terms how, when, and why to run each of our test suites to verify that thought capture remains friction-free.

---

## 1. The Three Levels of Testing

NotesFlare uses three tiers of testing to ensure full reliability from database transactions to pixel-perfect UI interactions:

| Test Suite | Targets | Speed | Why It Matters |
|---|---|---|---|
| **Backend Tests** | Database operations, timezone freezing, API routes. | ⚡ Super Fast (<3s) | Guarantees notes are captured correctly and bursts continue or break correctly according to the 30-minute continuity rule. |
| **Frontend Unit Tests** | React components (`BurstBlock`) and hooks (`useAutosave`). | ⚡ Fast (<2s) | Ensures components render correctly and user typing triggers the 1000ms debounced autosave. |
| **End-to-End (E2E) Tests** | Full stack integration using system Google Chrome. | 🕒 Moderate (~15s) | Wipes the database, spins up the backend and Next.js, and tests typing, sidebar navigation, and session restores inside a real browser. |

---

## 2. Command Reference: How to Run the Tests

We have created dedicated, fully automated runner scripts in the `scripts/` directory. You can invoke them using the shortcut commands mapped inside `package.json`.

Run all commands from the **project root directory**:

### 🏃‍♂️ Quick Shortcuts (Recommended)

*   **Run all tests (Backend & Frontend Unit):**
    ```bash
    npm run test
    ```
*   **Run Backend Tests:**
    ```bash
    npm run test:backend
    ```
*   **Run Frontend Unit Tests:**
    ```bash
    npm run test:frontend
    ```
*   **Run End-to-End Browser Tests:**
    ```bash
    npm run test:e2e
    ```

---

## 3. When to Use the Tests

To keep the development cycle smooth and robust, follow these guidelines:

### 🟢 1. During Feature Development
*   **When:** You are editing a specific frontend hook or component.
*   **Action:** Run frontend tests in **watch mode** so they rerun automatically when you hit save:
    ```bash
    npm run test:frontend:watch
    ```
*   **When:** You are editing a backend service or database logic.
*   **Action:** Run backend tests in **watch mode**:
    ```bash
    npm run test:backend:watch
    ```

### 🟡 2. Before committing code (`git commit`)
*   **Action:** Run the backend and frontend unit tests to ensure you haven't introduced any regression or syntax errors:
    ```bash
    npm run test
    ```

### 🔴 3. Before releasing or merging a Pull Request
*   **Action:** Run the E2E test suite. This starts a real browser and walks through actual user behaviors (navigation, typing, and session reloads).
    ```bash
    npm run test:e2e
    ```

---

## 4. Diagnostics & Troubleshooting: What if a test fails?

We have configured our tests to print **actionable diagnostic messages** for any failure. When a test fails, you don't need to sift through unreadable stack traces. Look at the test output directly:

*   **If a Backend Test fails:** Look for timezone or clock issues (we use `freezegun` to mock time). Make sure you didn't bypass `now` variables in SQLite queries.
*   **If a Frontend Unit Test fails:** Check the debounce delay in `useAutosave.ts` (must be `1000ms`) or verify that state updates are wrapped in `@testing-library/react`'s `act()`.
*   **If an E2E Test fails:**
    *   Playwright automatically saves a **screenshot of the failure** to `test-results/`.
    *   It also writes a markdown file `error-context.md` detailing the visual page layout and the exact locator failure.
    *   To view the HTML report and visually debug, run:
        ```bash
        npx playwright show-report coverage/e2e
        ```
