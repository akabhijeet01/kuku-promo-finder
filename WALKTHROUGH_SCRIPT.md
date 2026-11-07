# 3-Minute Video Walkthrough Script 🎥

**Assignment:** Kuku AI Generalist Assignment — Problem 1: Find the Promos  
**Candidate:** Abhijeet Kumar  
**Format:** Screen recording with voiceover (Loom / YouTube Unlisted / Google Drive)  
**Target Duration:** 2 minutes 45 seconds – 3 minutes  

---

## ⏱️ Video Outline & Speaking Guide

### Part 1: Problem & Approach (0:00 – 0:45)
- **Visual:** Open browser tab on GitHub repo or terminal showing the 50 episode screenplay files.
- **Voiceover:**
  > *"Hi everyone, I’m Abhijeet Kumar. Today I’m walking you through my solution for Problem 1: finding viral promo ads from microdrama screenplays for Kuku’s show 'I Married a Broken Soldier. He was a Duke'.*
  > 
  > *Microdramas live and die by their paid acquisition ads on TikTok, Instagram, and Shorts. Today, human editors watch every 2-minute episode manually. My goal was to build a tool that processes all 50 episodes in under two seconds, identifying high-converting 20 to 55-second promos with a scroll-stopping 3-second hook, an unresolved cliffhanger, and standalone clarity for cold audiences.*
  > 
  > *Instead of relying on an expensive LLM to read raw text, I designed a hybrid architecture: deterministic Python parsing, normalized emotional and physical spectacle density scoring, and an optional swappable LLM evaluation layer."*

---

### Part 2: Live Prototype Demo (0:45 – 1:45)
- **Visual:** Switch to Streamlit Web UI (`streamlit run app.py` running in browser).
- **Voiceover:**
  > *"Here is the interactive Streamlit dashboard. In the sidebar, an editor can choose either the bundled 50-episode season or upload new screenplay files.*
  > 
  > *Let’s click **Find Promos**. In less than a second, the tool parsed 50 screenplays, evaluated over 6,900 sliding windows, and extracted the top ranked promos.*
  > 
  > *Let’s look at Rank #1: Episode 24, from 20 seconds to 40 seconds. The hook line occurs right at the start: Juliana says 'I heard her. I thought Her Grace needed help.' Prudence confronts her over the poisoned Duchess's bed: 'No, my lady.' It delivers high-stakes suspicion with only 2 characters, so someone with zero context instantly understands the tension.*
  > 
  > *Now look at Rank #3: This is a cross-episode juxtaposition ad. It pairs Juliana being framed for poison in Episode 28 with the conspirators being arrested for high treason in Episode 43. This delivers the classic problem-and-payoff structure that generates twice the click-through rate on social ads.*
  > 
  > *Editors can filter by episode, adjust minimum score thresholds, inspect the exact dialogue and action beats, and export everything directly to JSON or Markdown with one click."*

---

### Part 3: Scale, Economics & Quality Limits (1:45 – 2:45)
- **Visual:** Show `SOLUTION_DOC.pdf` and terminal running `python3 generate_full_outputs.py`.
- **Voiceover:**
  > *"How does this scale to every show Kuku produces?*
  > 
  > *The rule-based engine runs at zero marginal cost in 1.2 seconds on a single CPU core. When connecting an LLM like Gemini 2.0 Flash for semantic nuance, batching candidate promos costs under one cent per 50-episode season. Because the LLM is isolated behind a single clean function, the model can be swapped instantly to Claude or open-weights.*
  > 
  > *Now, where does the tool pick badly? As an AI Generalist, being honest about failure modes is critical:*
  > 1. *First, the tool reads screenplay text, not video footage. It cannot see if an actor delivered a line flatly or if a silent 2-second stare was mesmerizing.*
  > 2. *Second, prolonged visual choreography like sword fights without spoken lines can be underscored compared to verbal arguments.*
  > 3. *Third, on multi-episode splices, the narrative cut works, but an editor still needs to check audio room tone and music transitions.*
  > 
  > *One place AI initially got it wrong during development was length bias: raw keyword accumulation favored 55-second clips. I diagnosed this and refactored the algorithm to normalize drama density strictly per 30 seconds and penalize crowded scenes with over four characters.*
  > 
  > *Thank you for your time, and I look forward to walking through the solution further in the interview!"*
