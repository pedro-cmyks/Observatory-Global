# GitHub CLI Setup for Observatory Global

This guide explains how to grant the necessary permissions for GitHub CLI to manage projects, issues, and automation.

---

## Required Permissions

To enable full GitHub CLI functionality for Observatory Global, the following Personal Access Token (PAT) scopes are required:

### Essential Scopes
```
repo              # Full control of private repositories
read:org          # Read org and team membership
write:org         # Write org and team membership
project           # Full control of projects
read:project      # Read access to projects
admin:org_hook    # Full control of organization hooks
```

### Why Each Scope Is Needed

| Scope | Purpose | Used For |
|-------|---------|----------|
| `repo` | Create and manage issues, PRs | Issue creation (#13-17), PR automation |
| `read:org` | View organization structure | Team assignments, org-level projects |
| `write:org` | Manage org teams | Assign issues to teams |
| `project` | Create and manage project boards | Iteration 3 project board, kanban automation |
| `read:project` | Read project data | Query project status, roadmaps |
| `admin:org_hook` | Manage webhooks | Automation triggers, CI/CD integration |

---

## Setup Instructions

### Option 1: Refresh Existing Token (Recommended)

If you already have GitHub CLI authenticated:

```bash
# Refresh with additional scopes
gh auth refresh -s project,read:project,write:org,admin:org_hook

# Verify new permissions
gh auth status
```

**Expected Output:**
```
✓ Logged in to github.com account pedro-cmyks (keyring)
✓ Git operations protocol: ssh
✓ Token: ghp_************************************
✓ Token scopes: gist, project, read:org, read:project, repo, write:org, admin:org_hook
```

### Option 2: Create New Fine-Grained Token

For more security, use a fine-grained PAT with minimal access:

1. **Navigate to GitHub Settings**
   - Go to: https://github.com/settings/tokens?type=beta
   - Click "Generate new token"

2. **Configure Token**
   - **Name:** `Observatory Global CLI Access`
   - **Expiration:** 90 days (or custom)
   - **Repository access:** Selected repositories → `Observatory-Global`

3. **Select Permissions**

   **Repository permissions:**
   - Contents: Read and write
   - Issues: Read and write
   - Pull requests: Read and write
   - Metadata: Read-only (auto-selected)

   **Organization permissions:**
   - Members: Read-only
   - Projects: Read and write

4. **Generate and Save Token**
   ```bash
   # Copy token (starts with ghp_)
   export GITHUB_TOKEN=ghp_your_token_here

   # Login with token
   gh auth login --with-token <<< $GITHUB_TOKEN
   ```

### Option 3: Use OAuth App Token (Most Secure)

```bash
# Login interactively with OAuth
gh auth login

# Select:
# - GitHub.com
# - SSH
# - Yes (login with web browser)

# Then add scopes:
gh auth refresh -s project,read:project,write:org
```

---

## Verification

After setup, verify all permissions work:

```bash
# Test issue management
gh issue list

# Test project access (this should no longer fail)
gh project create --title "Test Project" --owner pedro-cmyks

# Test label management
gh label list

# Test PR operations
gh pr list
```

---

## Current Limitations

Based on the error we encountered:

```
error: your authentication token is missing required scopes [project read:project]
To request it, run:  gh auth refresh -s project,read:project
```

**Problem:** The current token lacks `project` and `read:project` scopes.

**Impact:**
- ❌ Cannot create project boards via CLI
- ❌ Cannot automate issue → project assignments
- ❌ Cannot query project status programmatically

**Workaround Until Fixed:**
- Create projects manually in GitHub web UI
- Use GitHub Actions for automation (uses GITHUB_TOKEN with full permissions)

---

## Recommended Token Configuration

For Observatory Global development, use:

### Development Token (pedro-cmyks)
```yaml
scopes:
  - repo                 # Issues, PRs, code
  - read:org            # Team visibility
  - write:org           # Team assignments
  - project             # Project boards
  - read:project        # Project queries
  - admin:org_hook      # Webhooks for automation
  - workflow            # GitHub Actions (optional)
```

### CI/CD Token (GitHub Actions)
```yaml
# Already has these via GITHUB_TOKEN
permissions:
  contents: write
  issues: write
  pull-requests: write
  projects: write
```

---

## Security Best Practices

1. **Use Fine-Grained Tokens**
   - Limit to specific repositories
   - Set expiration dates (90 days recommended)
   - Rotate regularly

2. **Store Securely**
   ```bash
   # Use gh built-in credential manager (recommended)
   gh auth login

   # Or environment variable (temporary)
   export GITHUB_TOKEN=ghp_***

   # Never commit tokens to git!
   ```

3. **Audit Token Usage**
   ```bash
   # Check which scopes are active
   gh auth status

   # List recent API calls
   gh api /user/repos --paginate
   ```

4. **Revoke Unused Tokens**
   - Review tokens at: https://github.com/settings/tokens
   - Delete any that are no longer needed
   - Rotate compromised tokens immediately

---

## Automation Setup

Once permissions are granted, enable these automations:

### Auto-Assign Issues to Project
```yaml
# .github/workflows/assign-to-project.yml
name: Assign to Project

on:
  issues:
    types: [opened, labeled]

jobs:
  assign:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/add-to-project@v0.5.0
        with:
          project-url: https://github.com/users/pedro-cmyks/projects/1
          github-token: ${{ secrets.GH_PROJECT_TOKEN }}
```

### Auto-Label Issues
```yaml
# .github/workflows/auto-label.yml
name: Auto Label

on:
  issues:
    types: [opened]

jobs:
  label:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/labeler@v4
        with:
          repo-token: ${{ secrets.GITHUB_TOKEN }}
```

### Move Issues on PR Merge
```yaml
# .github/workflows/pr-merged.yml
name: Move to Done

on:
  pull_request:
    types: [closed]

jobs:
  move:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    steps:
      - name: Move to Done
        run: |
          gh project item-edit \
            --project-id $PROJECT_ID \
            --field-name "Status" \
            --field-value "Done"
```

---

## Troubleshooting

### Error: "not found" when creating project
```bash
gh project create --title "Test" --owner pedro-cmyks
# Error: resource not found
```

**Solution:** Ensure `project` scope is in token
```bash
gh auth refresh -s project
```

### Error: "forbidden" when listing labels
```bash
gh label list
# Error: HTTP 403: Forbidden
```

**Solution:** Ensure `repo` scope is in token
```bash
gh auth refresh -s repo
```

### Error: "bad credentials"
```bash
gh auth status
# Error: authentication token invalid
```

**Solution:** Re-authenticate
```bash
gh auth logout
gh auth login
```

---

## Next Steps After Setup

Once permissions are granted:

1. **Create Iteration 3 Project Board**
   ```bash
   gh project create \
     --title "Iteration 3: Narrative Intelligence Layer" \
     --owner pedro-cmyks
   ```

2. **Add Issues to Project**
   ```bash
   gh project item-add <project-id> --url https://github.com/pedro-cmyks/Observatory-Global/issues/13
   gh project item-add <project-id> --url https://github.com/pedro-cmyks/Observatory-Global/issues/14
   # ... repeat for #15, #16, #17
   ```

3. **Set Up Custom Fields**
   ```bash
   gh project field-create <project-id> \
     --name "Priority" \
     --data-type "SINGLE_SELECT" \
     --single-select-options "High,Medium,Low"

   gh project field-create <project-id> \
     --name "Sprint" \
     --data-type "SINGLE_SELECT" \
     --single-select-options "Week 1,Week 2,Week 3,Week 4,Week 5"
   ```

---

**Document Version:** 1.0
**Last Updated:** 2025-01-14
**Maintained By:** DevOps + Orchestrator
