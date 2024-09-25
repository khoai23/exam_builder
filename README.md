Ideal plan for the main system is just to be fool-proof exam tool (e.g generating problem so that learning the thing is the simpler way to do exams).
Ideal plan for the game is to get kids to run on faction-styled meritocratic game board. Great kids should learn that they can't be everywhere at one; Mediocre kids should see how fun it is to be great; Bad kids would be somewhat demoralized I guess, but at least they should be "contributing" e.g intrinsically better than a bot.

All possible extension regard the builder:
- [ ] \(Exam) Procedurally generated problems (~~algebraic~~ and geometric)
- [ ] \(Study) Mouse-driven, or later touch-driven geometric drawer (drawing parallel line, same length, perpendicular, etc.)
- [ ] \(Study) Option to show relevant solution with wrong answers
- [ ] \(System) Drag-n-drop categorizer
- [ ] \(System) User management (add, delete, change roles etc.)
- [ ] \(Game) Appropriate adjustable botting options
- [ ] \(Game) Paradox style map, TODO turn this into an unified map exporter thing too 
- [ ] \(Game) Fine-grained map with unique divisions for immersion
- [ ] \(Game) __IMPORTANT__ Mode for tactical-level battles between divisions
- [ ] \(Game) Defection and or rebellion

Remaining bugfix/missing features:
- [ ] \(System) Session expiration & archive 
- [ ] \(System) Button to flag possible duplicate items (remove or confirm as not-duplicate)
- [ ] \(System) Loading icon while performing modifying action e.g import/rollback 
- [ ] \(System) Commit-type import to prevent stupidity
- [ ] \(System) Mechanism to notify and show appropriate logs when failure/wrong format etc. happens
- [ ] \(Exam) Single manager capable of modifying score composition & recalculate for all students
- [ ] \(Game) Game board invalid connection at edge; likely leftover from the extended 4-corner
- [ ] \(Game) Occasional failure when creating a map (invalid polygon)
- [ ] \(Game) Mechanism to attack a region with a combined force of neighbor regions
- [ ] \(Game) Mechanism for player actions to execute concurrently instead of sequentially. 

Finished:
- [x] Data source organized by category
- [x] Integrate the current game map into a game board
- [x] Shared & persistent last category, used for both Build & Modify
- [x] Single manager capable of modifying settings (time limit, range, etc.)
- [x] Mechanism to do a test for increased coefficient of attacks and/or defense 
- [x] Mechanism to show actions done by last phase
- [x] \(System) Dynamic designation are being lumped with LaTeX's grouping signature e.g x_{2a}. This will likely cause problem for complex signatures. Need some way to completely move away from it.

Now defunct (still remaining, but too unimportant compare to the rest):
- [ ] \(System) Converter supporting doc file (only docx for now)
- [ ] \(System) Converter supporting multiple-choice question selection; exporting in the more generic xlsx instead.
- [ ] \(System) Converter direct import and copy content to clipboard (right now not working on Firefox)
- [ ] \(System) Import supporting xls file by xlrd
- [ ] \(System) Image support is only in solo mode; import image should support inline as default as well
