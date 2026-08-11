# Asset Swarm

## What it is

A media-production swarm for producing checked asset libraries: HTML animations rendered to video by the host, idempotent image-generation batches, HTML diagrams rendered to retina PNG, and real screen captures. Workers author sources or execute exact commands; checks render, execute, and validate the actual media.

This pattern keeps browser and recording work on the host side, where sandboxed workers cannot reliably launch browsers, while still making every worker output visible in Ringer.

## When to use

Use this when a post, landing page, video, or product launch needs a batch of reusable media assets. It is strongest when the orchestrator has already read the draft or product context and can map every asset to a specific beat rather than asking for generic visuals.

## Fill in

| Placeholder | What goes there |
|---|---|
| `{{ANIMATION_DESIGN_TOKENS}}` | Colors, fonts, stage constraints, and motion rules for animation workers. |
| `{{ANIMATION_KEY}}` | Short slug for one animation task and its rendered output prefix. |
| `{{ANIMATION_STORYBOARD}}` | Rich paragraph describing the exact 12-second loop and visual sequence. |
| `{{CAPTURE_DURATION_SECONDS}}` | Number of seconds the host recorder should capture. |
| `{{CAPTURE_KEY}}` | Short slug for one real capture task and output prefix. |
| `{{CAPTURE_URL}}` | Local or live URL the host recorder should capture. |
| `{{CAPTURE_VIEWPORT}}` | Viewport and device state to record, such as `1920x1080 desktop`. |
| `{{DIAGRAM_BRIEF}}` | Diagram content, labels, data, and layout intent. |
| `{{DIAGRAM_KEY}}` | Short slug for one diagram task. |
| `{{ENGINE_BUILD}}` | Engine name for HTML animation, diagram, and capture-planning tasks. |
| `{{ENGINE_CHEAP}}` | Engine name for mechanical image batch execution. |
| `{{IMAGE_BATCH_COMMANDS}}` | Exact idempotent shell commands to generate the batch images. |
| `{{IMAGE_BATCH_KEY}}` | Short slug for the image batch task. |
| `{{IMAGE_MIN_BYTES}}` | Minimum PNG byte size for generated stills. |
| `{{IMAGE_OUTPUT_1}}` | First expected PNG filename. |
| `{{IMAGE_OUTPUT_2}}` | Second expected PNG filename. |
| `{{IMAGE_OUTPUT_3}}` | Third expected PNG filename. |
| `{{IMAGE_PROMPTS_DIR}}` | Directory containing filled image prompt files. |
| `{{IMAGE_SUBJECT}}` | Subject paragraph for one generated still. |
| `{{KIT_DIR}}` | Absolute path to `templates/asset-swarm` after copying or installing this kit. |
| `{{NO_TEXT_RULE}}` | Explicit no-text instruction for generated images. |
| `{{PROJECT_NAME}}` | Project, post, product, or campaign name. |
| `{{RENDER_ANIM_SCRIPT}}` | Host-side script that renders HTML or URL captures to video. |
| `{{RENDER_SHOT_SCRIPT}}` | Host-side script that renders HTML to a retina PNG. |
| `{{RUN_SLUG}}` | Stable run slug for this asset set. |
| `{{SHARED_STYLE_BLOCK}}` | Shared visual style block reused across image prompts. |
| `{{WORKDIR}}` | Scratch run directory outside any source repo. |

## Checks

Animation, diagram, and capture checks run host-side render commands and then assert the generated media exists and has substance. Image-batch checks verify every expected PNG exists, has PNG magic bytes, and clears a byte floor.

This cannot be gamed by a worker saying the file is done: the check executes the renderer or validates the generated files. Failures name the missing source, failed render command, missing output, or undersized file so the retry prompt has usable evidence.

## Mix with

Use `launch-kit` before this kit when the asset set should be grounded in a finished launch story. Use `repo-feature` when captures or diagrams need a real app route built first. Use `adversarial-review` after the asset run when claims, captions, or generated diagrams need independent review.

## Gotchas

Render-as-check outputs are created after `expect_files` is asserted. Keep check-produced MP4, WebM, screenshots, and rendered PNG files out of `expect_files`; declare only worker-authored source files such as `anim.html`, `diagram.html`, or `capture-plan.md`, or leave `expect_files` empty on pure render tasks and explain that fallback harvest will collect the outputs.

Generated-image tasks are different: workers produce the PNGs directly, so image outputs belong in `expect_files`.

Seedance video tasks are also direct media-generation tasks. Start from `seedance.manifest.json`, keep both `video.mp4` and `generation.json` in `expect_files`, and use `checks/check_generated_video.py` to verify the MP4 signature plus the metadata byte count and SHA-256. The `seedance` engine calls OpenRouter's paid Video API directly; it is not an OpenCode text lane. Lint the filled manifest before choosing to run it, and treat the `usage` object in `generation.json` as the cost record.

For any image command that can exceed about two minutes under OpenCode, use `nohup` plus polling. Long foreground bash calls can be killed by the tool before the image API returns; a background log and poll loop makes the task idempotent and debuggable.

No text in generated images. Use HTML-authored animations and diagrams for readable labels because browser-rendered text is crisp and checkable.

Real captures should show the actual product or local page. Hide private data first; do not record production accounts unless the user explicitly approved it.

Heading regexes in downstream checks should tolerate numbering, and check-produced files must stay out of `expect_files` because pre-check assertions run before renderers.
