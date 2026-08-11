# ANSWER

The official Bland documentation does **not** document a selectable named LLM for an SMS Conversational Pathway, either per node, per pathway version, or per SMS-number configuration. The pathway GET reference documents node-level `data.modelOptions`, but names only `interruptionThreshold` and `temperature`; it does not name a model-selection member. That is consistent with the measured production object, whose `modelOptions` blocks contain operational settings but no model name.

Bland does document a boolean `use_candidate_model` on **pathway chat creation** (`POST /v1/pathway/chat/create`). This is a conversation/test-time switch, not a field in a pathway node or pathway-version graph. The docs describe it only as selecting “an experimental model version”; they do not identify the underlying provider/model, list model choices, promise Anthropic Sonnet-class capability, or document the flag on the SMS conversation endpoints.

Therefore, the public docs do not establish that the production SMS pathway can be upgraded to Sonnet-class (or another named smarter tier) through the API currently used to create versions.

FEASIBLE: UNKNOWN reason=Official docs expose only an unnamed candidate-model boolean for pathway chat, not a named model field accepted by pathway version-create or SMS APIs

# FIELD DETAILS

- **Node level:** documented path is `nodes[].data.modelOptions`, but its documented members are only `interruptionThreshold` and `temperature`. No model-name/member is documented there.
- **Pathway/version level:** the create-version body documents only top-level `name`, `nodes`, and `edges`. Its node schema allows `data` plus unspecified node-specific properties, but it does not name any model selector.
- **Conversation/test level:** `use_candidate_model` is a top-level boolean in the body of `POST /v1/pathway/chat/create`. It selects an unnamed experimental candidate for that chat instance.
- **SMS-number/account level:** `POST /v1/sms/number/update` documents the SMS number configuration, including `temperature`, `pathway_id`, `pathway_version`, and `start_node_id`, but no model selector. The docs do not identify an account-level model-selection setting.

# ALLOWED VALUES

- For `use_candidate_model`, the documented type is boolean, so the API surface shown supports `true` or `false`. Bland does not publish named candidate values or map the candidate to Anthropic, Sonnet, OpenAI, or any comparable tier.
- The `base` and `turbo` values documented elsewhere apply to non-pathway call/web-agent configuration. The Web Agent reference explicitly warns that setting a pathway resets `model`, so those values are not evidence of a pathway model selector.
- The official Dev Terminal page lists Claude models for the developer assistant that edits pathways. Those are the Dev Terminal assistant's models, not documented runtime models for pathway/SMS conversations.

# HOW TO SET IT VIA VERSION-CREATE

There is no documented way to set a named runtime LLM through `POST /v1/pathway/{pathway_id}/version`. The request schema accepts `name`, `nodes`, and `edges`; the documented node properties do not include a model selector. Do **not** invent `nodes[].data.modelOptions.model`, `model`, or a pathway-level field from the public docs.

The only documented candidate switch is used when creating a pathway chat, separately from version creation:

```json
{
  "pathway_id": "<id>",
  "pathway_version": 3,
  "use_candidate_model": true
}
```

This does not prove support for production SMS. The SMS create/send/configuration references omit `use_candidate_model`, and the November 17, 2025 changelog says it was added to “pathway chat creation,” not pathway version creation or SMS configuration.

# CONSTRAINTS

- SMS is documented as Enterprise-only.
- Bland's October 13, 2025 changelog says “Added candidate model support for SMS conversations,” but the current SMS API references do not expose or define a candidate-model field. The public docs therefore leave an implementation gap: they announce capability without documenting how to select it in the SMS API, which plans/accounts receive it beyond SMS's Enterprise gate, or what model it actually uses.
- No public official source reviewed names an Anthropic Sonnet-class runtime option for SMS pathways. The Sonnet names found in official docs belong to Bland's Dev Terminal assistant, a separate development tool.

# CITATIONS

1. https://docs.bland.ai/api-v1/get/pathway
   - Exact schema text: “`modelOptions`” followed by “`interruptionThreshold` — The sensitivity to interruptions at this node” and “`temperature` — The temperature of the model.”
   - This reference names no model-selection field within `modelOptions`.

2. https://docs.bland.ai/api-v1/post/create_pathway_version
   - Exact endpoint description: “Creates a new version of a specific pathway, including its name, nodes, and edges.”
   - Exact request text: “An array of node objects defining the structure of the pathway.”
   - Exact node text: “`data` — Object containing node-specific data” and “Other properties specific to the node type.”
   - The page does not name a model field or allowed model values.

3. https://docs.bland.ai/api-v1/post/pathway-chat-create
   - Exact field text: “`use_candidate_model`” (type: “boolean”).
   - Exact description: “Whether to use the candidate model for this pathway chat. When enabled, the pathway will use an experimental model version for enhanced performance and capabilities.”
   - Exact version text: “The specific version number of the pathway to use for this chat instance. If not provided, the production version will be used.”

4. https://docs.bland.ai/tutorials/pathways
   - Exact testing text: “Use Candidate Model — Test your pathway against a candidate model before promoting it.”

5. https://docs.bland.ai/api-v1/post/sms-update
   - Exact gating text: “Enterprise Feature - SMS is only available on Enterprise plans. Contact your Bland representative for access.”
   - Exact temperature text: “The model’s temperature setting, controlling creativity.”
   - Exact linkage text: “The ID of the linked conversational pathway (if any).” and “The specific version of the pathway to use.”
   - The documented body contains no model or candidate-model selector.

6. https://docs.bland.ai/api-v1/post/sms-create
   - Exact endpoint description: “Create an SMS conversation with specific pathway state without triggering immediate message sending.”
   - The documented body includes `curr_pathway_id`, `curr_pathway_version`, and `current_node_id`, but names no model or candidate-model field.

7. https://docs.bland.ai/api-v1/post/sms-send
   - The documented request has no model or candidate-model field.

8. https://www.bland.ai/changelog/2025-10-13-voice-knowledge-base-sms-web-agents-personas-call-logs-and-pathway-improvements
   - Exact SMS changelog text: “Added candidate model support for SMS conversations”.

9. https://www.bland.ai/changelog/2025-11-17-pathways-call-logs-personas-sms-and-api-improvements
   - Exact API changelog text: “Added support for `use_candidate_model` and `pathway_version` fields in pathway chat creation.”

10. https://docs.bland.ai/api-v1/post/agents
    - Exact pathway warning: “Setting a pathway will set the following fields to `null` / their default value - `prompt`, `first_sentence`, `model`, `dynamic_data`, `tools`, `transfer_list`”.
    - Exact non-pathway model text: “Select a model to use for your call. Options: `base` or `turbo`.”

11. https://docs.bland.ai/sdks/dev-terminal
    - Exact scope text: “An interactive AI-powered development REPL for building phone agents. Powered by Claude.”
    - Exact command text: “`/model` | List models or switch (`/model claude-sonnet-4-6`)”.
    - This page concerns the development REPL, not the pathway/SMS runtime.
