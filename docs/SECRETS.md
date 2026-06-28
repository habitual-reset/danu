# How to add API keys (no chat, no code editing)

## Recommended: drop file

1. In Finder, go to your home folder → `danu`
2. Duplicate `.secrets-drop.example` and rename the copy to `.secrets-drop`
   - Or in Terminal: `cp ~/danu/.secrets-drop.example ~/danu/.secrets-drop`
3. Open `.secrets-drop` with **TextEdit**
4. Paste your keys after the `=` signs (one per line):

   ```
   OPENAI_API_KEY=sk-proj-...paste here...
   LLM_MODEL=gpt-4.1-mini
   LLM_CONSOLIDATION_MODEL=gpt-4.1
   ```

5. Save and close TextEdit
6. In chat, say: **"import my secrets drop file"**

The agent will merge into `.env`, delete `.secrets-drop`, and confirm **without showing your keys**.

## Or: run the import script yourself

```bash
~/danu/scripts/import-secrets.sh
```

## Rules

- **Never** paste keys in chat
- `.secrets-drop` and `.env` are gitignored — they never go to GitHub
- Delete `.secrets-drop` after import (script/agent does this automatically)
- Rotate any key that was ever pasted in chat

## OpenAI key

https://platform.openai.com/api-keys → Create secret key → paste into `.secrets-drop` only