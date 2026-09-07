# Local Jira PAT setup

The Jira PAT is a credential, not chat input. Never paste it into ChatGPT,
agent instructions, source files, screenshots, `.env`, or command arguments.

## First-time setup

1. Revoke any PAT previously shared in chat or another untrusted location.
2. Create a new PAT in Jira for your own account, with an expiry date.
3. Connect to the Sage VPN/network if required.
4. From the repository root, run:

   ```powershell
   & ".\scripts\setup-jira-access.ps1" -JiraUrl "https://jira.sage.com"
   ```

5. Enter the new PAT only in the masked terminal prompt.

The installer verifies `/rest/api/2/myself`, encrypts the PAT with Windows
DPAPI for the current user, restricts the credential file permissions, and
installs the project-local Codex agent. The encrypted credential is stored at:

```text
%LOCALAPPDATA%\SageIntacctQA\jira-auth.json
```

It is not stored in this repository or OneDrive. Another Windows user must run
the installer with their own PAT.

## Safe verification

```powershell
python -m integrations.jira_pat_client verify
```

## Collect a Jira intake package

```powershell
python -m integrations.jira_pat_client collect IADSSL-1792 --download-attachments
```

The default output is `outputs/jira/<JIRA-KEY>/jira-intake.json` with any
attachments under the same issue directory.

## Jira writes

Comment and attachment commands are blocked unless `--confirm-write` is
provided. The local workflow may use that flag only after the user approves
the HTML report, complete comment draft, and evidence list.

## Rotation or removal

Re-run the installer to replace the encrypted credential. Revoke the old PAT
in Jira. To remove local access, delete:

```text
%LOCALAPPDATA%\SageIntacctQA\jira-auth.json
```
