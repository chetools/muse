# Watch for Sealed Takes and Grade Them

## Purpose

Grade a student's sealed spoken-explanation takes without the student pasting a session code for each take. A one-time setup stores the student's watch credentials and installs a lightweight poll: every minute a small script asks the course server whether a sealed take is waiting, and only a "yes" wakes Muse. The woken Muse fetches the pending list, grades each take with the keypoints grading skill, `local-keypoints-grading`, and reports the feedback in the chat. The student can also ask for a check at any moment instead of waiting for the next poll.

Grading itself is unchanged: it follows the `local-keypoints-grading` skill exactly, take by take, under the session code the server lists. This skill only finds the takes and hands them over.

## Trigger

Apply this skill when:

- the student pastes the watch setup block from the teacher's email (it carries the course server address, a grading token, and a poll key, under a heading naming this skill), or asks to set up the grading watch; or
- the student says "check now", "check for my take", "grade my take", or "grade my take now"; or
- a watch-grading poll wake arrives (a sealed take is waiting).

## Setup (one time, from the teacher's emailed block)

The emailed block gives three values: the course server address, the grading token, and the poll key. The token and the poll key are credentials. Handle them as follows, throughout this skill: write them only into the config file below; never print them in the chat, never echo them in a report, summary, or file name, and never send them anywhere except the configured course server.

1. **Write the config.** Create `watch-config.json` in this skill's folder with exactly the emailed values:

   ```json
   {"server": "<course server address>", "token": "<grading token>", "pollKey": "<poll key>"}
   ```

   Confirm to the student only that the config is written — not its contents.
2. **Write the poll script.** Copy `scripts/poll.sh.template` from this skill's folder to `~/hooks/scripts/watch-grading-poll.sh`, replacing the placeholder `__CONFIG_PATH__` in the copy with the absolute path of the `watch-config.json` written in step 1, and make the copy executable. The script holds no credential itself: it reads the poll key from the config at run time.
3. **Register the hook.** Use the hooks tools to add a hook with id `watch-grading`, the script path from step 2, a polling interval of 60 seconds, and this wake instruction, word for word:

   > A sealed take is waiting to be graded. Run the wake procedure of the local-watch-grading skill: fetch the pending list with `scripts/watch.mjs pending`, grade each listed take with the local-keypoints-grading skill under its session code, and report each take's feedback and grades in the chat. If the pending list is empty, report nothing.
4. **Test, then enable.** Dry-run the hook. A `silent` decision means the poll reached the server and nothing is waiting; a `wake` decision means a take is already waiting (grading it is fine — enable the hook first, then run the wake procedure once). If the dry run reports a script error, fix the script and dry-run again. Then enable the hook.
5. **Report the setup.** Tell the student the watch is on: their Muse now checks every minute, grading starts on its own when a take seals, and they can say "check now" at any time to grade a take immediately.

If the grading skill (`local-keypoints-grading`) is not installed on this Muse, say so during setup and point the student to the skill link in the teacher's email; the watch can still be installed, but a take cannot be graded until the skill is.

## Wake procedure (a poll found a waiting take)

1. **Fetch the pending list.** Run `node scripts/watch.mjs pending` (the script sits in this skill's `scripts/` folder; it reads the config itself). The output is `{"takes": [{examId, title, sessionCode, status, sealedAt}]}`. Fetching the list claims each take for 15 minutes: grade what this fetch returned, and do not fetch again to check on the same takes.
2. **Empty list.** If `takes` is empty, the take was already picked up (for example by a manual check). Report nothing and stop.
3. **Grade each take** with the `local-keypoints-grading` skill, using the server address from the config and the take's `sessionCode`: follow that skill's procedure for the session code (packet, sealed audio, local Parakeet transcription and correction, key, grade, upload, standing grade).
4. **Report in the chat.** For each take, show the exam title and the report the grading skill prescribes — the feedback, the per-point grades, and the standing grade. One message may cover several takes; keep each take's feedback under its own title.

## Manual pickup ("check now")

When the student says "check now", "check for my take", "grade my take", or "grade my take now", run the wake procedure at once, in this chat, starting at step 1: fetch the pending list and grade whatever it returns, with the same per-take reports. The student does not need the session code — the list is the source of it. The 15-minute claim still applies, so a manual check and a poll wake never grade the same take twice.

If the pending list is empty, say so plainly: no sealed take is waiting to be graded. If the config is missing, the watch was never set up here: ask the student for the teacher's emailed block and run the setup. If the helper exits with the 401 message, apply the Limits below.

## Limits

- The token and the poll key are sent only to the course server address stored in `watch-config.json` — the token as the `X-Watch-Token` header of the pending request, the poll key as the `X-Poll-Key` header of poll requests. Never put either value in a URL, a chat message, a report, or any other file than the config.
- A 401 from either endpoint means the teacher revoked or regenerated the credential. Do not retry with altered values and do not guess a new one: tell the student to ask the teacher to re-email the watch setup, then run the setup again with the new block (the teacher's re-email carries the current token; re-running setup replaces the config and the old credentials stop working).
- Grade only takes the pending list returns, under the session codes it lists. Audio or a transcript the student hands over directly is never graded through this skill — a take not served by the course server under a listed session code is not the sealed take.
- This skill never marks a take final and never changes a grade after upload; the grading skill's own limits govern every take it grades.
