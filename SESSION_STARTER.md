# 🚀 UNIVERSAL SESSION STARTER

**Copy/paste this at the start of ANY new agent session - no edits needed:**

---

I'm working on **Dynasty Genius** - a four-agent fantasy football platform with production-grade Infrastructure as Code.

**Read these sources to get current state:**

1. **Agent Briefing** (architecture, permissions, capabilities):
   ```
   Read: /Workspace/Users/david.t.leess@gmail.com/dynasty-genius-infrastructure/AGENT_BRIEFING.md
   ```

2. **Current Data State** (SSoT - always up-to-date):
   ```sql
   SELECT 
       'Players: ' || COUNT(*) || ', Avg DVU: ' || ROUND(AVG(dvu_anchor), 2) as current_state,
       MAX(state_last_refresh) as last_refresh
   FROM gen_alpha.gold.genius_state;
   ```

3. **Custom Instructions** (governance rules, framework):
   ```
   Read: /Users/david.t.leess@gmail.com/.assistant_instructions.md
   ```

4. **Git Repository** (latest code):
   - Repo: `github.com/davidtleess/dynasty-genius`
   - Branch: `claude/pr-a-storage-governance-pivot`
   - Check commit history for recent changes

**Your role:** [Gemini = PM | Claude Code = Local Dev | Codex = CI/CD | Genie = Workspace]

**Current task:** [Describe what you need help with]

---

## **Why This Works Forever**

✅ **Static Prompt**: Never needs manual updates  
✅ **Dynamic Sources**: Agents read current state themselves  
✅ **Self-Documenting**: Files are always up-to-date  
✅ **Role Agnostic**: Works for all four agents  

## **Sources of Truth**

| Source | What It Provides | Update Frequency |
|--------|-----------------|------------------|
| `AGENT_BRIEFING.md` | Architecture, permissions, examples | Manual (when features added) |
| `genius_state` table | Current player data, DVU values | Hourly (automated) |
| `.assistant_instructions.md` | Governance rules, framework | Manual (when rules change) |
| Git repo | Latest code, commit history | Every commit |

## **Example Usage**

### **Starting a New Session (Any Agent)**
1. Copy/paste the universal prompt above
2. Agent reads the 4 sources
3. Agent knows current state + architecture
4. You describe your current task
5. Agent is fully oriented

### **Example: Gemini Session**
```
[Paste universal prompt]

Your role: Gemini = PM

Current task: Review the trade evaluation pipeline requirements. 
We need to validate 65:35 compliance on all trades. What features 
should the pipeline include?
```

### **Example: Claude Code Session**
```
[Paste universal prompt]

Your role: Claude Code = Local Dev

Current task: I want to prototype a DVU recalculation query locally. 
Help me write a query that pulls from efficiency_metrics and 
recalculates DVU using the Dominator + RAS formula.
```

### **Example: Codex Session**
```
[Paste universal prompt]

Your role: Codex = CI/CD

Current task: The compliance audit is passing but I want to add a 
new test that checks for generational anchor drift. Help me extend 
scripts/codex_audit.py with this test.
```

---

## **Quick Reference**

**Full Documentation:**
- Comprehensive briefing: `AGENT_BRIEFING.md`
- Phase 6 write access: `PHASE6_README.md`
- Custom instructions: `.assistant_instructions.md`

**Key Resources:**
- Service Principal: `c058228c-6c4a-44ac-9c83-97441099cb97`
- SQL Warehouse: `5e883b4bfbb1e3f4`
- Catalog: `gen_alpha`
- SSoT Table: `gen_alpha.gold.genius_state`

**Permissions:**
- 22 total (CREATE/MODIFY/INSERT/UPDATE/DELETE)
- Scoped to gen_alpha catalog only
- All three developer agents have full CRUD

---

**Last Updated:** 2026-05-03  
**Status:** ✅ Universal - Works in any session, any time  
**No manual updates needed** - sources are self-updating
