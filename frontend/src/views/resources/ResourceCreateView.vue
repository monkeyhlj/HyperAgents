<template>
  <div class="page-shell">
    <Row :gutter="16">
      <Col v-if="isAgentKind" :xs="24" :lg="8">
        <Card dis-hover class="chat-test-card">
          <template #title>
            <Space>
              <span>Dialog Test</span>
              <Tag color="green">Draft</Tag>
            </Space>
          </template>

          <Alert show-icon>
            Fill model settings and system prompt first, then use this chat to dry-run agent behavior.
          </Alert>

          <div class="chat-messages">
            <div v-if="testMessages.length === 0" class="chat-empty">No test message yet.</div>
            <div v-for="(item, idx) in testMessages" :key="idx" class="chat-message" :class="`role-${item.role}`">
              <div class="chat-role">{{ item.role }}</div>
              <div class="chat-text">{{ item.text }}</div>
            </div>
          </div>

          <Input v-model="testInput" type="textarea" :rows="3" placeholder="Type prompt for test" />
          <Space style="margin-top: 10px">
            <Button @click="clearTest">Clear</Button>
            <Button type="primary" :loading="testing" @click="runDraftTest">Send</Button>
          </Space>
        </Card>
      </Col>

      <Col :xs="24" :lg="isAgentKind ? 16 : 24">
        <Card dis-hover>
          <template #title>
            <Space>
              <Button size="small" @click="goBack">Back</Button>
              <span>{{ pageTitle }}</span>
              <Tag v-if="isEditMode" color="orange">Edit Mode</Tag>
            </Space>
          </template>

          <Form :model="form" label-position="top">
            <Row :gutter="16">
              <Col :xs="24" :md="24">
                <FormItem label="Project">
                  <Select v-model="form.project_id" filterable placeholder="Select project" @on-change="handleProjectChange">
                    <Option v-for="item in projects" :key="item.id" :value="item.id">{{ item.name }} ({{ item.id }})</Option>
                  </Select>
                </FormItem>
              </Col>
            </Row>

            <Row :gutter="16">
              <Col :xs="24" :md="12">
                <FormItem label="Name">
                  <Input v-model="form.name" maxlength="120" show-word-limit />
                </FormItem>
              </Col>
              <Col :xs="24" :md="12">
                <FormItem label="Visibility">
                  <Select v-model="form.visibility">
                    <Option value="private">private</Option>
                    <Option value="project">project</Option>
                    <Option value="public">public</Option>
                  </Select>
                </FormItem>
              </Col>
            </Row>

            <FormItem label="Description">
              <Input v-model="form.description" type="textarea" :rows="3" maxlength="1000" show-word-limit />
            </FormItem>

            <Alert v-if="isKnowledgeKind" show-icon type="info" style="margin-bottom: 16px">
              <template #desc>
                <strong>📚 Knowledge Base Creation Guide</strong>
                <div style="margin-top: 8px; line-height: 1.6;">
                  <div>1️⃣ Fill in the basic information (name, description, config)</div>
                  <div>2️⃣ Click <strong>"Create"</strong> button below</div>
                  <div>3️⃣ You'll be automatically redirected to the <strong>Document Management</strong> page</div>
                  <div>4️⃣ Upload your documents (PDF, DOCX, MD, TXT) on that page</div>
                </div>
              </template>
            </Alert>

            <Alert v-if="isSkillKind" show-icon type="info" style="margin-bottom: 16px">
              <template #desc>
                <strong>🚀 Skill Creation Guide</strong>
                <div style="margin-top: 8px; line-height: 1.6;">
                  <div>1️⃣ Fill in the basic information (name, description, config)</div>
                  <div>2️⃣ Click <strong>"Create"</strong> button below</div>
                  <div>3️⃣ You'll be automatically redirected to the <strong>Skill Detail</strong> page</div>
                  <div>4️⃣ Upload your Skill package (.zip with SKILL.md and scripts/) on that page</div>
                </div>
              </template>
            </Alert>

            <Row v-if="isAgentKind" :gutter="16">
              <Col :xs="24" :md="12">
                <FormItem label="Agent Run Mode">
                  <Select v-model="form.run_mode">
                    <Option value="llm">llm (model inference)</Option>
                    <Option value="code">code (custom code execution)</Option>
                  </Select>
                </FormItem>
              </Col>
            </Row>

            <template v-if="isAgentKind">
              <Divider />

              <FormItem label="Model Preset">
                <RadioGroup v-model="form.model_mode">
                  <Radio label="default">Use default template</Radio>
                  <Radio label="custom">Custom model settings</Radio>
                </RadioGroup>
              </FormItem>

              <Row v-if="form.model_mode === 'default'" :gutter="16">
                <Col :xs="24" :md="12">
                  <FormItem label="Template">
                    <Select v-model="form.template_id" clearable filterable @on-change="applyTemplate">
                      <Option v-for="item in templates" :key="item.template_id" :value="item.template_id">
                        {{ item.name }} ({{ item.model_provider || '-' }} / {{ item.model_name || '-' }})
                      </Option>
                    </Select>
                  </FormItem>
                </Col>
              </Row>

              <template v-else>
                <FormItem label="Custom Model Source">
                  <RadioGroup v-model="form.provider_config_mode">
                    <Radio label="env">Env profile</Radio>
                    <Radio label="connection">URL + API Key</Radio>
                  </RadioGroup>
                </FormItem>

                <Row v-if="form.provider_config_mode === 'env'" :gutter="16">
                  <Col :xs="24" :md="8">
                    <FormItem label="Model Provider">
                      <Input v-model="form.model_provider" placeholder="openai / localhost / compatible provider" />
                    </FormItem>
                  </Col>
                  <Col :xs="24" :md="8">
                    <FormItem label="Model Name">
                      <Input v-model="form.model_name" placeholder="e.g. qwen-plus" />
                    </FormItem>
                  </Col>
                  <Col :xs="24" :md="8">
                    <FormItem label="Provider Profile">
                      <Input v-model="form.provider_profile" placeholder="e.g. qwen -> QWEN_* in .env" />
                    </FormItem>
                  </Col>
                </Row>

                <template v-else>
                  <Row :gutter="16">
                    <Col :xs="24" :md="12">
                      <FormItem label="Saved Provider Connection">
                        <Select v-model="form.provider_connection_id" clearable filterable placeholder="Select saved connection" @on-change="applyProviderConnection">
                          <Option v-for="item in providerConnections" :key="item.id" :value="item.id">
                            {{ item.name }} ({{ item.default_model || '-' }} / {{ item.api_key_masked || 'no key' }})
                          </Option>
                        </Select>
                      </FormItem>
                    </Col>
                    <Col :xs="24" :md="12">
                      <FormItem label="Connection Name">
                        <Input v-model="form.provider_connection_name" placeholder="Name for a new connection" />
                      </FormItem>
                    </Col>
                  </Row>

                  <Row :gutter="16">
                    <Col :xs="24" :md="8">
                      <FormItem label="Provider Type">
                        <Select v-model="form.provider_type">
                          <Option value="openai_compatible">openai_compatible</Option>
                        </Select>
                      </FormItem>
                    </Col>
                    <Col :xs="24" :md="16">
                      <FormItem label="Base URL">
                        <Input v-model="form.provider_base_url" placeholder="https://api.example.com/v1" />
                      </FormItem>
                    </Col>
                  </Row>

                  <Row :gutter="16">
                    <Col :xs="24" :md="16">
                      <FormItem label="API Key">
                        <Input v-model="form.provider_api_key" type="password" password placeholder="Only sent to backend; saved encrypted when you save connection" />
                      </FormItem>
                    </Col>
                    <Col :xs="24" :md="8">
                      <FormItem label="Actions">
                        <Space wrap>
                          <Button :loading="providerLoadingModels" @click="loadProviderModels">Load Models</Button>
                          <Button :loading="providerTesting" @click="testProviderDraft">Test</Button>
                          <Button type="primary" :loading="providerSaving" @click="saveProviderConnectionDraft">Save Connection</Button>
                        </Space>
                      </FormItem>
                    </Col>
                  </Row>

                  <Row :gutter="16">
                    <Col :xs="24" :md="12">
                      <FormItem label="Model">
                        <Select v-if="form.provider_model_options.length > 0" v-model="form.model_name" filterable allow-create placeholder="Select model">
                          <Option v-for="item in form.provider_model_options" :key="item" :value="item">{{ item }}</Option>
                        </Select>
                        <Input v-else v-model="form.model_name" placeholder="Enter model name manually if /models is unavailable" />
                      </FormItem>
                    </Col>
                    <Col :xs="24" :md="12">
                      <FormItem label="Model Provider">
                        <Input v-model="form.model_provider" placeholder="openai" />
                      </FormItem>
                    </Col>
                  </Row>

                  <Alert v-if="providerProbeResult" :type="providerProbeResult.ok ? 'success' : 'warning'" show-icon style="margin-bottom: 12px">
                    {{ providerProbeResult.ok ? `Loaded models: ${(providerProbeResult.models || []).length}` : (providerProbeResult.error || 'Load models failed; enter model manually') }}
                  </Alert>
                  <Alert v-if="providerTestResult" :type="providerTestResult.ok ? 'success' : 'error'" show-icon style="margin-bottom: 12px">
                    {{ providerTestResult.ok ? `Test success: ${providerTestResult.output_preview || '-'}` : (providerTestResult.error || 'Provider test failed') }}
                  </Alert>
                </template>
              </template>
              <Divider />

              <FormItem label="System Prompt">
                <Input v-model="form.system_prompt" type="textarea" :rows="4" placeholder="Define system behavior for this resource" />
              </FormItem>

              <Row :gutter="16">
                <Col :xs="24" :md="12">
                  <FormItem label="Associate Tools">
                    <Select v-model="form.tool_ids" multiple filterable>
                      <Option v-for="item in toolOptions" :key="item.id" :value="item.id">{{ item.name }}</Option>
                    </Select>
                  </FormItem>
                </Col>
                <Col :xs="24" :md="12">
                  <FormItem label="Associate Skills">
                    <Select v-model="form.skill_ids" multiple filterable>
                      <Option v-for="item in skillOptions" :key="item.id" :value="item.id">{{ item.name }}</Option>
                    </Select>
                  </FormItem>
                </Col>
              </Row>

              <Row :gutter="16">
                <Col :xs="24" :md="12">
                  <FormItem label="Associate MCPs">
                    <Select v-model="form.mcp_ids" multiple filterable>
                      <Option v-for="item in mcpOptions" :key="item.id" :value="item.id">{{ item.name }}</Option>
                    </Select>
                  </FormItem>
                </Col>
                <Col :xs="24" :md="12">
                  <FormItem label="Associate Knowledge Bases">
                    <Select v-model="form.knowledge_base_ids" multiple filterable>
                      <Option v-for="item in kbOptions" :key="item.id" :value="item.id">{{ item.name }}</Option>
                    </Select>
                  </FormItem>
                </Col>
              </Row>

              <Divider />

              <Alert show-icon class="authoring-guide-alert">
                <template #desc>
                  <div class="authoring-guide-copy">
                    <div>
                      <strong>Authoring guide:</strong>
                      <a :href="authoringGuideUrl" target="_blank" rel="noopener noreferrer">{{ authoringGuidePath }}</a>
                    </div>
                    <div>
                      `Custom Code` runs only in <strong>code</strong> mode. `Advanced Config JSON` is merged into `context.config` for both draft testing and saved execution.
                    </div>
                  </div>
                </template>
              </Alert>

              <FormItem label="Custom Code (Editable)">
                <CodeEditor
                  v-model="form.custom_code"
                  language="python"
                  min-height="260px"
                  placeholder="Write run(input_text, context) for code-mode agents"
                />
              </FormItem>
            </template>
            <template v-else>
              <Alert show-icon>
                {{ nonAgentHint }}
              </Alert>

              <template v-if="isToolKind">
                <Divider />

                <Row :gutter="16">
                  <Col :xs="24" :md="8">
                    <FormItem label="Tool Runtime">
                      <Select v-model="form.tool_runtime">
                        <Option value="python">python</Option>
                        <Option value="javascript">javascript</Option>
                      </Select>
                    </FormItem>
                  </Col>
                  <Col :xs="24" :md="8">
                    <FormItem label="Function Name">
                      <Input v-model="form.tool_entrypoint" placeholder="e.g. run" />
                    </FormItem>
                  </Col>
                  <Col :xs="24" :md="8">
                    <FormItem label="Shared In Project">
                      <Select v-model="form.tool_shared">
                        <Option :value="true">true</Option>
                        <Option :value="false">false</Option>
                      </Select>
                    </FormItem>
                  </Col>
                </Row>

                <FormItem label="Tool Code (Editable)">
                  <CodeEditor
                    v-model="form.tool_code"
                    :language="form.tool_runtime === 'javascript' ? 'javascript' : 'python'"
                    min-height="260px"
                    placeholder="Implement your tool function here"
                  />
                </FormItem>

                <Row :gutter="16">
                  <Col :xs="24" :md="12">
                    <FormItem label="Input Schema JSON">
                      <CodeEditor
                        v-model="form.tool_input_schema_json"
                        language="json"
                        min-height="200px"
                        placeholder="JSON Schema for tool input"
                      />
                    </FormItem>
                  </Col>
                  <Col :xs="24" :md="12">
                    <FormItem label="Output Schema JSON">
                      <CodeEditor
                        v-model="form.tool_output_schema_json"
                        language="json"
                        min-height="200px"
                        placeholder="JSON Schema for tool output"
                      />
                    </FormItem>
                  </Col>
                </Row>
              </template>

              <template v-else-if="isMcpKind">
                <Divider />

                <Row :gutter="16">
                  <Col :xs="24" :md="8">
                    <FormItem label="Transport">
                      <Select v-model="form.mcp_transport">
                        <Option value="streamable_http">streamable_http</Option>
                        <Option value="sse">sse (Server-Sent Events)</Option>
                        <Option value="stdio">stdio</Option>
                      </Select>
                    </FormItem>
                  </Col>
                  <Col :xs="24" :md="8">
                    <FormItem label="Timeout (seconds)">
                      <Input v-model="form.mcp_timeout_seconds" type="number" />
                    </FormItem>
                  </Col>
                  <Col :xs="24" :md="8">
                    <FormItem label="Quick Test">
                      <Space>
                        <Button :loading="mcpProbing" @click="probeMcpDraft">Test</Button>
                        <Button @click="showMcpTemplate = true">Template</Button>
                      </Space>
                    </FormItem>
                  </Col>
                </Row>

                <Row v-if="form.mcp_transport === 'streamable_http' || form.mcp_transport === 'sse'" :gutter="16">
                  <Col :xs="24" :md="24">
                    <FormItem label="Endpoint URL">
                      <Input v-model="form.mcp_endpoint_url" :placeholder="form.mcp_transport === 'sse' ? 'e.g. https://mcp.amap.com/sse?key=...' : 'e.g. http://127.0.0.1:8099'" />
                    </FormItem>
                  </Col>
                </Row>

                <Row v-else :gutter="16">
                  <Col :xs="24" :md="12">
                    <FormItem label="Command">
                      <Input v-model="form.mcp_command" placeholder="e.g. python" />
                    </FormItem>
                  </Col>
                  <Col :xs="24" :md="12">
                    <FormItem label="Args JSON">
                      <CodeEditor
                        v-model="form.mcp_args_json"
                        language="json"
                        min-height="120px"
                        placeholder='e.g. ["scripts/mock_mcp_server.py"]'
                      />
                    </FormItem>
                  </Col>
                </Row>

                <Row :gutter="16">
                  <Col :xs="24" :md="12">
                    <FormItem label="Headers JSON">
                      <CodeEditor
                        v-model="form.mcp_headers_json"
                        language="json"
                        min-height="120px"
                        placeholder='e.g. {"Authorization":"Bearer xxx"}'
                      />
                    </FormItem>
                  </Col>
                  <Col :xs="24" :md="12">
                    <FormItem label="Env JSON">
                      <CodeEditor
                        v-model="form.mcp_env_json"
                        language="json"
                        min-height="120px"
                        placeholder='e.g. {"MCP_TOKEN":"demo"}'
                      />
                    </FormItem>
                  </Col>
                </Row>

                <Alert v-if="mcpProbeResult" :type="mcpProbeResult.ok ? 'success' : 'error'" show-icon style="margin-bottom: 12px">
                  {{ mcpProbeResult.ok ? `Probe success, tools: ${mcpProbeResult.tools.join(', ') || '-'}` : (mcpProbeResult.error || 'Probe failed') }}
                </Alert>
              </template>
            </template>


            <template v-if="isWorkflowKind">
              <Divider />
              <div class="workflow-builder">
                <div class="workflow-toolbar">
                  <div>
                    <h3>Workflow Canvas</h3>
                    <p>Build an agent flow. Drag from a node handle to create branches; join nodes merge upstream outputs.</p>
                  </div>
                  <Space wrap>
                    <Button @click="syncWorkflowFromJson">Load from JSON</Button>
                    <Button type="primary" ghost @click="syncWorkflowToJson">Format JSON</Button>
                    <Button @click="addBranchFromSelected">Add Branch</Button>
                    <Button @click="addJoinNode">Add Join Node</Button>
                    <Button type="primary" @click="addWorkflowNode">Add Node</Button>
                  </Space>
                </div>

                <Row :gutter="16" class="workflow-meta-row">
                  <Col :xs="24" :md="6">
                    <FormItem label="Version">
                      <Input v-model="workflowDraft.version" />
                    </FormItem>
                  </Col>
                  <Col :xs="24" :md="6">
                    <FormItem label="Status">
                      <Select v-model="workflowDraft.status">
                        <Option value="draft">draft</Option>
                        <Option value="active">active</Option>
                        <Option value="paused">paused</Option>
                      </Select>
                    </FormItem>
                  </Col>
                  <Col :xs="24" :md="6">
                    <FormItem label="Timeout Seconds">
                      <Input v-model="workflowDraft.timeout_seconds" type="number" />
                    </FormItem>
                  </Col>
                  <Col :xs="24" :md="6">
                    <FormItem label="Max Retries">
                      <Input v-model="workflowDraft.max_retries" type="number" />
                    </FormItem>
                  </Col>
                </Row>

                <div class="workflow-canvas split-canvas">
                  <div class="workflow-flow-panel vue-flow-panel">
                    <div class="flow-panel-title">
                      <span>Flow</span>
                      <Space>
                        <Tag color="cyan">{{ workflowNodes.length }} nodes</Tag>
                        <Button size="small" @click="openWorkflowFullscreen">Fullscreen</Button>
                      </Space>
                    </div>
                    <VueFlow
                      class="workflow-vue-flow"
                      :nodes="workflowFlowNodes"
                      :edges="workflowFlowEdges"
                      :default-viewport="{ zoom: 0.9 }"
                      :min-zoom="0.35"
                      :max-zoom="1.5"
                      fit-view-on-init
                      @node-click="handleWorkflowNodeClick"
                      @node-drag-stop="handleWorkflowNodeDragStop"
                      @connect="handleWorkflowConnect"
                    >
                      <Background pattern-color="#c7d7ea" :gap="18" />
                      <Controls />
                      <template #node-default="nodeProps">
                        <div class="flow-card-node">
                          <div class="flow-card-head">
                            <strong>{{ nodeProps.data.label }}</strong>
                            <span>{{ nodeProps.data.outputMode }}</span>
                          </div>
                          <small>{{ nodeProps.data.sublabel }}</small>
                        </div>
                      </template>
                    </VueFlow>
                  </div>

                  <div class="workflow-editor-panel" v-if="selectedWorkflowNode">
                    <div class="editor-panel-heading">
                      <div>
                        <Tag color="blue">Selected Node</Tag>
                        <h3>{{ selectedWorkflowNode.name || selectedWorkflowNode.id }}</h3>
                      </div>
                      <Space>
                        <Button size="small" @click="addWorkflowNodeAfterSelected">Add After</Button>
                        <Button size="small" type="error" ghost :disabled="workflowNodes.length === 1" @click="removeSelectedWorkflowNode">Delete</Button>
                      </Space>
                    </div>

                    <Row :gutter="12">
                      <Col :xs="24" :md="8">
                        <FormItem label="Step ID">
                          <Input v-model="selectedWorkflowNode.id" placeholder="step_1" />
                        </FormItem>
                      </Col>
                      <Col :xs="24" :md="10">
                        <FormItem label="Node Name">
                          <Input v-model="selectedWorkflowNode.name" placeholder="Node name" />
                        </FormItem>
                      </Col>
                      <Col :xs="24" :md="6">
                        <FormItem label="Output Mode">
                          <Select v-model="selectedWorkflowNode.output_mode">
                            <Option value="text">text</Option>
                            <Option value="json">json</Option>
                          </Select>
                        </FormItem>
                      </Col>
                    </Row>

                    <FormItem label="Agent">
                      <Select v-model="selectedWorkflowNode.agent_id" filterable placeholder="Select project agent">
                        <Option v-for="agent in agentOptions" :key="agent.id" :value="agent.id">{{ agent.name }} ({{ agent.id }})</Option>
                      </Select>
                    </FormItem>

                    <FormItem label="Input Template">
                      <Input v-model="selectedWorkflowNode.input_text" type="textarea" :rows="5" placeholder="{{ input.task }} or use {{ steps.step_1.output }}" />
                    </FormItem>

                    <div class="connection-editor">
                      <div class="connection-header">
                        <strong>Connections</strong>
                        <span>Drag node handles on the canvas, or use Add Branch / Add Join Node.</span>
                      </div>
                      <div class="connection-groups">
                        <div>
                          <small>Upstream</small>
                          <div class="connection-tags">
                            <Tag v-for="node in upstreamNodesFor(selectedWorkflowNode)" :key="node.uid" color="geekblue">{{ node.name || node.id }}</Tag>
                            <span v-if="upstreamNodesFor(selectedWorkflowNode).length === 0" class="connection-empty">Start node</span>
                          </div>
                        </div>
                        <div>
                          <small>Downstream</small>
                          <div class="connection-tags">
                            <Tag v-for="node in downstreamNodesFor(selectedWorkflowNode)" :key="node.uid" color="cyan">{{ node.name || node.id }}</Tag>
                            <span v-if="downstreamNodesFor(selectedWorkflowNode).length === 0" class="connection-empty">End node</span>
                          </div>
                        </div>
                      </div>
                      <div v-if="outgoingEdgesFor(selectedWorkflowNode).length" class="edge-list">
                        <div v-for="edge in outgoingEdgesFor(selectedWorkflowNode)" :key="edge.id" class="edge-row">
                          <span>{{ selectedWorkflowNode.name || selectedWorkflowNode.id }} -> {{ nodeLabelByUid(edge.target) }}</span>
                          <Button size="small" type="error" ghost @click="removeWorkflowEdge(edge.id)">Remove</Button>
                        </div>
                      </div>
                    </div>

                    <div class="routing-editor">
                      <div class="routing-header">
                        <strong>Routing</strong>
                        <Button size="small" @click="addWorkflowRoute(selectedWorkflowNode)">Add Route</Button>
                      </div>
                      <div v-if="selectedWorkflowNode.routing.length === 0" class="routing-empty">No custom routing. It will continue to the next node.</div>
                      <div v-for="(routeItem, routeIndex) in selectedWorkflowNode.routing" :key="routeIndex" class="routing-row">
                        <Select v-model="routeItem.mode" class="route-mode-select">
                          <Option value="condition">condition</Option>
                          <Option value="default">default</Option>
                        </Select>
                        <Input v-if="routeItem.mode !== 'default'" v-model="routeItem.condition" placeholder="output.priority == 'high'" />
                        <Select v-model="routeItem.next" filterable placeholder="Next node">
                          <Option v-for="target in workflowNodes" :key="target.uid" :value="target.id" :disabled="target.uid === selectedWorkflowNode.uid">{{ target.name || target.id }}</Option>
                        </Select>
                        <Button size="small" type="error" ghost @click="selectedWorkflowNode.routing.splice(routeIndex, 1)">Remove</Button>
                      </div>
                    </div>
                  </div>
                </div>

                <FormItem label="Final Output JSON">
                  <CodeEditor v-model="workflowOutputJson" language="json" min-height="120px" />
                </FormItem>
              </div>
            </template>
            <FormItem v-if="showConfigEditor" :label="configEditorLabel">
              <Alert show-icon class="authoring-guide-alert">
                <template #desc>
                  <div class="authoring-guide-copy">
                    <div v-if="isMcpKind">
                      <strong>MCP advanced config:</strong>
                      Keep core fields in the MCP form above (transport / endpoint / command / timeout). Put optional extras here, such as auth strategies, feature flags, or routing hints.
                    </div>
                    <div v-else-if="isWorkflowKind">
                      <strong>Auto-synced Workflow Definition:</strong>
                      This JSON is generated from the canvas above while you edit nodes, routing, metadata, or output mapping.
                    </div>
                    <div v-else>
                      <strong>Advanced Config example:</strong>
                      provider_profile decides which .env prefix the backend reads. For example, provider_profile=qwen means QWEN_API_KEY / QWEN_BASE_URL / QWEN_DEFAULT_MODEL must exist in .env. role_name is optional and only used as a human-readable label inside the config.
                    </div>
                    <pre v-if="!isMcpKind && !isWorkflowKind" class="config-example-block">{
  "provider_profile": "qwen",
  "temperature": 0.2
}</pre>
                    <pre v-else class="config-example-block">{
  "feature_flags": {
    "allow_dynamic_tools": true
  },
  "metadata": {
    "owner": "platform"
  }
}</pre>
                  </div>
                </template>
              </Alert>
              <CodeEditor
                v-model="form.config_json"
                language="json"
                min-height="220px"
                placeholder="Add extra runtime settings such as provider_profile, role_name, temperature, routes, or feature flags"
              />
            </FormItem>

            <FormItem>
              <Space>
                <Button @click="goBack">Cancel</Button>
                <Button type="primary" :loading="saving" @click="submitForm">{{ submitLabel }}</Button>
              </Space>
            </FormItem>
          </Form>
        </Card>
      </Col>
    </Row>

    <Teleport to="body">
      <div v-if="isWorkflowKind && showWorkflowFullscreen" class="workflow-fullscreen-overlay">
        <div class="workflow-fullscreen-shell">
          <div class="workflow-fullscreen-toolbar">
            <div>
              <h3>Workflow Canvas</h3>
              <p>{{ workflowNodes.length }} nodes · {{ workflowEdges.length }} links · drag empty canvas to pan, wheel to zoom</p>
            </div>
            <Space wrap>
              <Button @click="addBranchFromSelected">Add Branch</Button>
              <Button @click="addJoinNode">Add Join Node</Button>
              <Button type="primary" @click="addWorkflowNode">Add Node</Button>
              <Button @click="requestWorkflowFitView">Fit View</Button>
              <Button @click="closeWorkflowFullscreen">Close</Button>
            </Space>
          </div>
          <VueFlow
            class="workflow-vue-flow fullscreen"
            :nodes="workflowFlowNodes"
            :edges="workflowFlowEdges"
            :default-viewport="{ zoom: 0.85 }"
            :min-zoom="0.15"
            :max-zoom="2.5"
            fit-view-on-init
            @node-click="handleWorkflowNodeClick"
            @node-drag-stop="handleWorkflowNodeDragStop"
            @connect="handleWorkflowConnect"
          >
            <Background pattern-color="#c7d7ea" :gap="18" />
            <Controls />
            <template #node-default="nodeProps">
              <div class="flow-card-node">
                <div class="flow-card-head">
                  <strong>{{ nodeProps.data.label }}</strong>
                  <span>{{ nodeProps.data.outputMode }}</span>
                </div>
                <small>{{ nodeProps.data.sublabel }}</small>
              </div>
            </template>
          </VueFlow>
        </div>
      </div>
    </Teleport>
    <!-- MCP Template Modal -->
    <Modal v-model="showMcpTemplate" title="MCP Recommended Template" ok-text="Copy Template" :loading="false" @on-ok="copyMcpTemplate">
      <div class="mcp-template-modal">
        <Alert show-icon style="margin-bottom: 12px">
          <template #desc>
            Below is the recommended complete MCP configuration structure. Click "Copy Template" to paste it into your form editors.
          </template>
        </Alert>

        <div class="template-section">
          <h4>Core Fields (MCP Form)</h4>
          <div class="template-code">
            <div class="code-line"><span class="key">transport</span>: <span class="value">streamable_http</span> (or stdio)</div>
            <div class="code-line"><span class="key">endpoint_url</span>: <span class="value">http://127.0.0.1:8099</span> (HTTP mode)</div>
            <div class="code-line"><span class="key">command</span>: <span class="value">python</span> (stdio mode)</div>
            <div class="code-line"><span class="key">timeout_seconds</span>: <span class="value">8</span></div>
          </div>
        </div>

        <Divider />

        <div class="template-section">
          <h4>Headers JSON</h4>
          <pre class="template-json">{{ mcpTemplateHeaders }}</pre>
          <p class="template-hint">🔑 Use for: Bearer token, API key, custom headers</p>
        </div>

        <div class="template-section">
          <h4>Env JSON</h4>
          <pre class="template-json">{{ mcpTemplateEnv }}</pre>
          <p class="template-hint">📝 Use for: Debug flags, MCP server config (HTTP mode: recorded but not sent; stdio mode: will be used)</p>
        </div>

        <div class="template-section">
          <h4>Advanced MCP Config JSON</h4>
          <pre class="template-json">{{ mcpTemplateAdvanced }}</pre>
          <p class="template-hint">⚙️ Use for: feature_flags, metadata, routing, retry policies</p>
        </div>

        <Divider />

        <Alert type="success" show-icon>
          <template #desc>
            <strong>Current Status:</strong> Only streamable_http is supported. stdio is planned for future release.
          </template>
        </Alert>
      </div>
    </Modal>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Message } from "view-ui-plus";
import { VueFlow, useVueFlow } from "@vue-flow/core";
import { Background } from "@vue-flow/background";
import { Controls } from "@vue-flow/controls";
import "@vue-flow/core/dist/style.css";
import "@vue-flow/core/dist/theme-default.css";
import "@vue-flow/controls/dist/style.css";
import CodeEditor from "../../components/CodeEditor.vue";
import { api } from "../../services/api";

const route = useRoute();
const router = useRouter();
const { fitView } = useVueFlow();

const projects = ref([]);
const templates = ref([]);
const ownedResources = ref([]);
const providerConnections = ref([]);
const saving = ref(false);
const testing = ref(false);
const mcpProbing = ref(false);
const providerLoadingModels = ref(false);
const providerTesting = ref(false);
const providerSaving = ref(false);
const showMcpTemplate = ref(false);
const testInput = ref("");
const testMessages = ref([]);
const loadedResource = ref(null);
const mcpProbeResult = ref(null);
const providerProbeResult = ref(null);
const providerTestResult = ref(null);
const providerConnectionLoadWarningShown = ref(false);
const workflowOutputJson = ref("{\n  \"summary\": \"{{ last.output }}\",\n  \"steps\": \"{{ steps }}\"\n}");
const workflowDraft = ref({
  version: "1.0.0",
  status: "draft",
  timeout_seconds: 300,
  max_retries: 0
});
const workflowNodes = ref([]);
const workflowEdges = ref([]);
const selectedWorkflowNodeUid = ref("");
const showWorkflowFullscreen = ref(false);

const form = ref({
  project_id: "",
  name: "",
  visibility: "project",
  description: "",
  model_mode: "default",
  run_mode: "llm",
  template_id: "",
  model_provider: "",
  model_name: "",
  provider_profile: "",
  provider_config_mode: "env",
  provider_connection_id: "",
  provider_connection_name: "",
  provider_type: "openai_compatible",
  provider_base_url: "",
  provider_api_key: "",
  provider_model_options: [],
  system_prompt: "",
  custom_code: "def run(input_text, context):\n    text = input_text.strip()\n\n    if text == \"ping\":\n        return call_tool(\"testping\", {\"action\": \"ping\", \"text\": text})\n\n    if text == \"show config\":\n        return {\n            \"project_id\": context.get(\"project_id\"),\n            \"tool_ids\": context.get(\"config\", {}).get(\"tool_ids\", []),\n            \"tools\": list_tools(),\n        }\n\n    return {\"echo\": text}\n",
  tool_runtime: "python",
  tool_entrypoint: "run",
  tool_shared: true,
  tool_code: "def run(input_data: dict, context: dict) -> dict:\n    # Implement tool logic here\n    return {\"ok\": True, \"echo\": input_data}\n",
  tool_input_schema_json: "{\n  \"type\": \"object\",\n  \"properties\": {\n    \"query\": { \"type\": \"string\" }\n  },\n  \"required\": [\"query\"]\n}",
  tool_output_schema_json: "{\n  \"type\": \"object\",\n  \"properties\": {\n    \"ok\": { \"type\": \"boolean\" },\n    \"echo\": { \"type\": \"object\" }\n  }\n}",
  mcp_transport: "streamable_http",
  mcp_endpoint_url: "http://127.0.0.1:8099",
  mcp_command: "",
  mcp_args_json: "[]",
  mcp_headers_json: "{}",
  mcp_env_json: "{}",
  mcp_timeout_seconds: "8",
  config_json: "{\n  \"provider_profile\": \"qwen\",\n  \"temperature\": 0.2\n}",
  tool_ids: [],
  skill_ids: [],
  mcp_ids: [],
  knowledge_base_ids: []
});

const kind = computed(() => route.meta.kind || "agent");
const isAgentKind = computed(() => kind.value === "agent");
const isToolKind = computed(() => kind.value === "tool");
const isMcpKind = computed(() => kind.value === "mcp");
const isSkillKind = computed(() => kind.value === "skill");
const isKnowledgeKind = computed(() => kind.value === "knowledge_base");
const isWorkflowKind = computed(() => kind.value === "workflow");
const pageTitle = computed(() => route.meta.title || "Create Resource");
const backRoute = computed(() => route.meta.backRoute || "resources-overview");
const isEditMode = computed(() => route.meta.mode === "edit");
const resourceId = computed(() => String(route.params.resourceId || ""));
const submitLabel = computed(() => (isEditMode.value ? "Save Changes" : "Create"));
const showConfigEditor = computed(() => !isToolKind.value);
const configEditorLabel = computed(() => {
  if (isAgentKind.value) {
    return "Advanced Config JSON (Editable)";
  }
  if (isToolKind.value) {
    return "Advanced Tool Config JSON";
  }

  if (isMcpKind.value) {
    return "Advanced MCP Config JSON (Editable)";
  }
  if (isWorkflowKind.value) {
    return "Workflow Definition JSON";
  }
  return "Config JSON";
});
const nonAgentHint = computed(() => {
  const map = {
    tool: "Tools are programmable helpers. Define function code and schema below. Tool resources can be reused by agents in the same project.",
    skill: "Skills orchestrate tools and logic. Put your composition settings in Config JSON.",
    mcp: "MCP resources are integration descriptors. Use Config JSON to define server and protocol options.",
    knowledge_base: "Knowledge resources are retrieval/config containers. Define datasource and indexing settings in Config JSON.",
    workflow: "Workflows orchestrate project agents with JSON steps, input templates, routing rules and final output mapping."
  };
  return map[kind.value] || "Configure this resource with Config JSON.";
});
const authoringGuidePath = "docs/modules/agents.zh-en.md";
const authoringGuideUrl = "https://github.com/monkeyhlj/HyperAgents/blob/main/docs/modules/agents.zh-en.md";

// MCP Template strings
const mcpTemplateHeaders = `{
  "Authorization": "Bearer your-jwt-token-here",
  "X-API-Key": "sk-1234567890",
  "X-Custom-Header": "value"
}`;

const mcpTemplateEnv = `{
  "DEBUG": "false",
  "LOG_LEVEL": "info",
  "MCP_FEATURE_FLAG_DYNAMIC_TOOLS": "true"
}`;

const mcpTemplateAdvanced = `{
  "feature_flags": {
    "allow_dynamic_tools": true,
    "enable_caching": false
  },
  "metadata": {
    "owner": "platform-team",
    "version": "v1.0.0",
    "tags": ["production"]
  },
  "routing": {
    "primary_endpoint": "http://primary:8000",
    "fallback_endpoint": "http://fallback:8000"
  },
  "retry": {
    "max_attempts": 3,
    "backoff_seconds": 2
  }
}`;

const scopedOwned = computed(() => {
  if (!form.value.project_id) {
    return [];
  }
  return ownedResources.value.filter((item) => item.project_id === form.value.project_id);
});

const toolOptions = computed(() => scopedOwned.value.filter((item) => item.kind === "tool"));
const skillOptions = computed(() => scopedOwned.value.filter((item) => item.kind === "skill"));
const mcpOptions = computed(() => scopedOwned.value.filter((item) => item.kind === "mcp"));
const kbOptions = computed(() => scopedOwned.value.filter((item) => item.kind === "knowledge_base"));
const agentOptions = computed(() => scopedOwned.value.filter((item) => item.kind === "agent"));
const selectedWorkflowNode = computed(() => workflowNodes.value.find((item) => item.uid === selectedWorkflowNodeUid.value) || workflowNodes.value[0] || null);
const workflowFlowNodes = computed(() => workflowNodes.value.map((node, index) => ({
  id: node.uid,
  type: "default",
  position: node.position || { x: 120 + index * 300, y: 140 },
  data: {
    label: `${index + 1}. ${node.name || node.id}`,
    sublabel: agentNameById(node.agent_id) || "No agent selected",
    outputMode: node.output_mode || "text"
  },
  selected: selectedWorkflowNodeUid.value === node.uid,
  class: selectedWorkflowNodeUid.value === node.uid ? "workflow-vue-node selected" : "workflow-vue-node"
})));
const workflowFlowEdges = computed(() => workflowEdges.value.map((edge) => ({
  id: edge.id,
  source: edge.source,
  target: edge.target,
  animated: true,
  type: "smoothstep"
})).filter((edge) => edge.source && edge.target));
const selectedProviderConnection = computed(() => {
  if (!form.value.provider_connection_id) {
    return null;
  }
  return providerConnections.value.find((item) => item.id === form.value.provider_connection_id) || null;
});

function defaultAdvancedConfigJsonByKind(targetKind) {
  if (targetKind === "mcp") {
    return "{\n  \"feature_flags\": {\n    \"allow_dynamic_tools\": true\n  },\n  \"metadata\": {\n    \"owner\": \"platform\"\n  }\n}";
  }
  if (targetKind === "agent") {
    return "{\n  \"provider_profile\": \"qwen\",\n  \"temperature\": 0.2\n}";
  }
  if (targetKind === "knowledge_base") {
    return "{\n  \"chunk_size\": 512,\n  \"chunk_overlap\": 50,\n  \"embedding_model\": \"openai:text-embedding-3-small\",\n  \"top_k\": 5,\n  \"similarity_threshold\": 0.7\n}";
  }
  if (targetKind === "workflow") {
    return "{\n  \"version\": \"1.0.0\",\n  \"status\": \"draft\",\n  \"timeout_seconds\": 300,\n  \"max_retries\": 0,\n  \"steps\": [\n    {\n      \"id\": \"step_1\",\n      \"name\": \"First agent step\",\n      \"agent_id\": \"replace-with-agent-id\",\n      \"input\": {\n        \"text\": \"{{ input.task }}\"\n      },\n      \"output_mode\": \"text\"\n    }\n  ],\n  \"output\": {\n    \"summary\": \"{{ last.output }}\",\n    \"steps\": \"{{ steps }}\"\n  }\n}";
  }
  return "{}";
}


function makeWorkflowNode(index = workflowNodes.value.length) {
  const stepNumber = index + 1;
  return {
    uid: `${Date.now()}_${Math.random().toString(16).slice(2)}`,
    id: `step_${stepNumber}`,
    name: `Step ${stepNumber}`,
    agent_id: agentOptions.value[0]?.id || "",
    input_text: index === 0 ? "{{ input.task }}" : `{{ steps.step_${index}.output }}`,
    output_mode: "text",
    position: { x: 120 + index * 300, y: 140 },
    routing: []
  };
}

function ensureWorkflowNodes() {
  if (workflowNodes.value.length === 0) {
    workflowNodes.value = [makeWorkflowNode(0)];
  }
  if (!selectedWorkflowNodeUid.value || !workflowNodes.value.some((item) => item.uid === selectedWorkflowNodeUid.value)) {
    selectedWorkflowNodeUid.value = workflowNodes.value[0]?.uid || "";
  }
}

function makeWorkflowEdge(source, target) {
  return { id: `edge_${source}_${target}_${Date.now()}_${Math.random().toString(16).slice(2)}`, source, target };
}

function addWorkflowEdge(source, target) {
  if (!source || !target || source === target) {
    return;
  }
  const sourceExists = workflowNodes.value.some((node) => node.uid === source);
  const targetExists = workflowNodes.value.some((node) => node.uid === target);
  if (!sourceExists || !targetExists) {
    return;
  }
  const exists = workflowEdges.value.some((edge) => edge.source === source && edge.target === target);
  if (!exists) {
    workflowEdges.value.push(makeWorkflowEdge(source, target));
  }
}

function removeWorkflowEdge(edgeId) {
  workflowEdges.value = workflowEdges.value.filter((edge) => edge.id !== edgeId);
}

function handleWorkflowConnect(params) {
  addWorkflowEdge(params?.source, params?.target);
}

function addWorkflowNode() {
  const node = makeWorkflowNode(workflowNodes.value.length);
  workflowNodes.value.push(node);
  selectedWorkflowNodeUid.value = node.uid;
  requestWorkflowFitView();
}

function addWorkflowNodeAfterSelected() {
  const selectedIndex = workflowNodes.value.findIndex((item) => item.uid === selectedWorkflowNodeUid.value);
  const insertIndex = selectedIndex >= 0 ? selectedIndex + 1 : workflowNodes.value.length;
  const node = makeWorkflowNode(insertIndex);
  if (selectedIndex >= 0) {
    const selected = workflowNodes.value[selectedIndex];
    node.input_text = `{{ steps.${selected.id}.output }}`;
    node.position = { x: (selected.position?.x ?? 120) + 300, y: selected.position?.y ?? 140 };
  }
  workflowNodes.value.splice(insertIndex, 0, node);
  if (selectedIndex >= 0) {
    addWorkflowEdge(workflowNodes.value[selectedIndex].uid, node.uid);
  }
  selectedWorkflowNodeUid.value = node.uid;
  requestWorkflowFitView();
}

function addBranchFromSelected() {
  const selected = selectedWorkflowNode.value;
  if (!selected) {
    return;
  }
  const branchCount = outgoingEdgesFor(selected).length;
  const node = makeWorkflowNode(workflowNodes.value.length);
  node.name = `Branch ${branchCount + 1}`;
  node.id = `branch_${workflowNodes.value.length + 1}`;
  node.input_text = `{{ steps.${selected.id}.output }}`;
  node.position = {
    x: (selected.position?.x ?? 120) + 320,
    y: (selected.position?.y ?? 140) + branchCount * 150 - 60
  };
  workflowNodes.value.push(node);
  addWorkflowEdge(selected.uid, node.uid);
  selectedWorkflowNodeUid.value = node.uid;
  requestWorkflowFitView();
}

function addJoinNode() {
  const terminalNodes = workflowNodes.value.filter((node) => outgoingEdgesFor(node).length === 0);
  const sources = terminalNodes.length > 0 ? terminalNodes : workflowNodes.value.slice(-1);
  const node = makeWorkflowNode(workflowNodes.value.length);
  node.name = "Join Review";
  node.id = `join_${workflowNodes.value.length + 1}`;
  node.input_text = sources.map((source) => `${source.name || source.id}: {{ steps.${source.id}.output }}`).join("\n\n");
  const maxX = Math.max(...sources.map((source) => source.position?.x ?? 120));
  const avgY = Math.round(sources.reduce((sum, source) => sum + (source.position?.y ?? 140), 0) / Math.max(1, sources.length));
  node.position = { x: maxX + 340, y: avgY };
  workflowNodes.value.push(node);
  sources.forEach((source) => addWorkflowEdge(source.uid, node.uid));
  selectedWorkflowNodeUid.value = node.uid;
  requestWorkflowFitView();
}

function removeWorkflowNode(index) {
  if (workflowNodes.value.length <= 1) {
    return;
  }
  const removed = workflowNodes.value[index];
  workflowNodes.value.splice(index, 1);
  workflowEdges.value = workflowEdges.value.filter((edge) => edge.source !== removed.uid && edge.target !== removed.uid);
  workflowNodes.value.forEach((node) => {
    node.routing = (node.routing || []).filter((routeItem) => routeItem.next !== removed.id);
  });
  selectedWorkflowNodeUid.value = workflowNodes.value[Math.min(index, workflowNodes.value.length - 1)]?.uid || "";
}

function selectWorkflowNode(uid) {
  selectedWorkflowNodeUid.value = uid;
}

function removeSelectedWorkflowNode() {
  const index = workflowNodes.value.findIndex((item) => item.uid === selectedWorkflowNodeUid.value);
  if (index >= 0) {
    removeWorkflowNode(index);
  }
}

function agentNameById(agentId) {
  return agentOptions.value.find((item) => item.id === agentId)?.name || "";
}

function nodeLabelByUid(uid) {
  const node = workflowNodes.value.find((item) => item.uid === uid);
  return node ? (node.name || node.id) : uid;
}

function incomingEdgesFor(node) {
  if (!node) return [];
  return workflowEdges.value.filter((edge) => edge.target === node.uid);
}

function outgoingEdgesFor(node) {
  if (!node) return [];
  return workflowEdges.value.filter((edge) => edge.source === node.uid);
}

function upstreamNodesFor(node) {
  return incomingEdgesFor(node).map((edge) => workflowNodes.value.find((item) => item.uid === edge.source)).filter(Boolean);
}

function downstreamNodesFor(node) {
  return outgoingEdgesFor(node).map((edge) => workflowNodes.value.find((item) => item.uid === edge.target)).filter(Boolean);
}

function openWorkflowFullscreen() {
  showWorkflowFullscreen.value = true;
  requestWorkflowFitView();
}

function closeWorkflowFullscreen() {
  showWorkflowFullscreen.value = false;
}
function requestWorkflowFitView() {
  nextTick(() => {
    try {
      fitView({ padding: 0.2, duration: 240 });
    } catch {
      // Vue Flow can be unmounted while route changes; ignore transient fit errors.
    }
  });
}

function handleWorkflowNodeClick(event) {
  const node = event?.node || event;
  if (node?.id) {
    selectWorkflowNode(node.id);
  }
}

function handleWorkflowNodeDragStop(event) {
  const node = event?.node || event;
  const target = workflowNodes.value.find((item) => item.uid === node?.id);
  if (target && node?.position) {
    target.position = { x: node.position.x, y: node.position.y };
  }
}

function addWorkflowRoute(node) {
  node.routing.push({ mode: "condition", condition: "output.status == 'ok'", next: workflowNodes.value.find((item) => item.uid !== node.uid)?.id || "" });
}

function syncWorkflowFromJson() {
  let definition;
  try {
    definition = parseAdvancedConfig();
  } catch (error) {
    Message.error(error.message || "Workflow JSON is invalid");
    return;
  }
  loadWorkflowDraftFromDefinition(definition);
  Message.success("Workflow canvas loaded from JSON");
}

function syncWorkflowToJson() {
  try {
    const definition = buildWorkflowDefinitionFromCanvas();
    form.value.config_json = JSON.stringify(definition, null, 2);
    Message.success("Workflow JSON updated from canvas");
  } catch (error) {
    Message.error(error.message || "Workflow canvas is invalid");
  }
}

function loadWorkflowDraftFromDefinition(definition) {
  const data = definition && typeof definition === "object" ? definition : {};
  workflowDraft.value = {
    version: data.version || "1.0.0",
    status: data.status || "draft",
    timeout_seconds: data.timeout_seconds || 300,
    max_retries: data.max_retries || 0
  };
  workflowOutputJson.value = JSON.stringify(data.output || { summary: "{{ last.output }}", steps: "{{ steps }}" }, null, 2);
  const steps = Array.isArray(data.steps) ? data.steps : [];
  workflowNodes.value = steps.map((step, index) => ({
    uid: `${Date.now()}_${index}_${Math.random().toString(16).slice(2)}`,
    id: step.id || `step_${index + 1}`,
    name: step.name || `Step ${index + 1}`,
    agent_id: step.agent_id || "",
    input_text: typeof step.input === "string" ? step.input : (step.input?.text || ""),
    output_mode: step.output_mode || "text",
    position: step.position || { x: 120 + index * 300, y: 140 },
    routing: (step.routing || []).map((routeItem) => ({
      mode: routeItem.default ? "default" : "condition",
      condition: routeItem.condition || "",
      next: routeItem.next || ""
    }))
  }));
  ensureWorkflowNodes();

  const uidByStepId = new Map(workflowNodes.value.map((node) => [node.id, node.uid]));
  const edges = [];
  const addEdgeFromStepIds = (sourceId, targetId) => {
    const source = uidByStepId.get(sourceId);
    const target = uidByStepId.get(targetId);
    if (!source || !target || source === target) {
      return;
    }
    if (!edges.some((edge) => edge.source === source && edge.target === target)) {
      edges.push(makeWorkflowEdge(source, target));
    }
  };

  steps.forEach((step, index) => {
    const sourceId = String(step.id || `step_${index + 1}`);
    const nextItems = Array.isArray(step.next) ? step.next : (step.next ? [step.next] : []);
    nextItems.forEach((targetId) => addEdgeFromStepIds(sourceId, String(targetId)));
    const dependsOnItems = Array.isArray(step.depends_on) ? step.depends_on : (step.depends_on ? [step.depends_on] : []);
    dependsOnItems.forEach((dependencyId) => addEdgeFromStepIds(String(dependencyId), sourceId));
  });

  if (edges.length === 0 && workflowNodes.value.length > 1) {
    workflowNodes.value.slice(0, -1).forEach((node, index) => {
      edges.push(makeWorkflowEdge(node.uid, workflowNodes.value[index + 1].uid));
    });
  }
  workflowEdges.value = edges;
  updateWorkflowJsonFromCanvas();
  requestWorkflowFitView();
}

function updateWorkflowJsonFromCanvas() {
  if (!isWorkflowKind.value || workflowNodes.value.length === 0) {
    return;
  }
  try {
    const definition = buildWorkflowDefinitionFromCanvas();
    form.value.config_json = JSON.stringify(definition, null, 2);
  } catch {
    // Keep the user's current JSON visible while the canvas has incomplete edits.
  }
}

function buildWorkflowDefinitionFromCanvas() {
  ensureWorkflowNodes();
  const nodeByUid = new Map(workflowNodes.value.map((node) => [node.uid, node]));
  const usedIds = new Set();
  const steps = workflowNodes.value.map((node, index) => {
    const id = (node.id || "").trim();
    if (!id) {
      throw new Error(`Node ${index + 1} step ID is required`);
    }
    if (usedIds.has(id)) {
      throw new Error(`Duplicate step ID: ${id}`);
    }
    usedIds.add(id);
    if (!node.agent_id) {
      throw new Error(`Node ${index + 1} must select an Agent`);
    }
    const routing = (node.routing || [])
      .filter((routeItem) => routeItem.next)
      .map((routeItem) => {
        if (routeItem.mode === "default") {
          return { default: true, next: routeItem.next };
        }
        return { condition: routeItem.condition || "", next: routeItem.next };
      });
    const next = outgoingEdgesFor(node).map((edge) => nodeByUid.get(edge.target)?.id).filter(Boolean);
    const dependsOn = incomingEdgesFor(node).map((edge) => nodeByUid.get(edge.source)?.id).filter(Boolean);
    return {
      id,
      name: node.name || id,
      agent_id: node.agent_id,
      input: { text: node.input_text || "" },
      output_mode: node.output_mode || "text",
      position: node.position || { x: 120 + index * 300, y: 140 },
      ...(next.length ? { next } : {}),
      ...(dependsOn.length ? { depends_on: dependsOn } : {}),
      ...(routing.length ? { routing } : {})
    };
  });
  let output;
  try {
    output = JSON.parse(workflowOutputJson.value || "{}");
  } catch {
    throw new Error("Final Output JSON is invalid");
  }
  return {
    version: workflowDraft.value.version || "1.0.0",
    status: workflowDraft.value.status || "draft",
    timeout_seconds: Number(workflowDraft.value.timeout_seconds || 300),
    max_retries: Number(workflowDraft.value.max_retries || 0),
    steps,
    output
  };
}
function applyCreateDefaultsByKind() {
  if (isEditMode.value) {
    return;
  }
  form.value.config_json = defaultAdvancedConfigJsonByKind(kind.value);
  if (isWorkflowKind.value) {
    loadWorkflowDraftFromDefinition(JSON.parse(form.value.config_json));
    updateWorkflowJsonFromCanvas();
  }
}

function goBack() {
  router.push({ name: backRoute.value });
}

async function loadProjects() {
  projects.value = await api.listProjects();
  if (projects.value.length > 0 && !form.value.project_id) {
    form.value.project_id = projects.value[0].id;
  }
}

async function loadTemplates() {
  if (!isAgentKind.value) {
    templates.value = [];
    return;
  }
  templates.value = await api.listDefaultResources({ kind: kind.value });
}

async function loadOwnedResources() {
  ownedResources.value = await api.listOwnedResources();
}

async function loadProviderConnections(options = {}) {
  const { notify = false } = options;
  if (!isAgentKind.value || !form.value.project_id) {
    providerConnections.value = [];
    return;
  }
  try {
    providerConnections.value = await api.listProviderConnections(form.value.project_id);
  } catch (error) {
    providerConnections.value = [];
    if (notify && !providerConnectionLoadWarningShown.value) {
      providerConnectionLoadWarningShown.value = true;
      Message.warning(error.message || "Provider connections are unavailable");
    }
  }
}

async function loadResource() {
  if (!isEditMode.value || !resourceId.value) {
    return;
  }
  loadedResource.value = await api.getResource(resourceId.value);
  const config = loadedResource.value.config || {};
  form.value.project_id = loadedResource.value.project_id || "";
  form.value.name = loadedResource.value.name || "";
  form.value.visibility = loadedResource.value.visibility || "project";
  form.value.description = loadedResource.value.description || "";
  form.value.run_mode = config.run_mode || "llm";
  form.value.model_mode = loadedResource.value.model_provider || loadedResource.value.model_name || loadedResource.value.provider_connection_id ? "custom" : "default";
  form.value.template_id = "";
  if (isAgentKind.value) {
    form.value.model_provider = loadedResource.value.model_provider || "";
    form.value.model_name = loadedResource.value.model_name || "";
    form.value.provider_profile = loadedResource.value.provider_profile || "";
    form.value.provider_connection_id = loadedResource.value.provider_connection_id || config.provider_connection_id || "";
    form.value.provider_config_mode = form.value.provider_connection_id ? "connection" : "env";
    const savedConnection = providerConnections.value.find((item) => item.id === form.value.provider_connection_id);
    form.value.provider_model_options = savedConnection?.model_list_cache || [];
    form.value.system_prompt = config.system_prompt || "";
    form.value.custom_code = config.custom_code || "";
    form.value.tool_ids = config.tool_ids || [];
    form.value.skill_ids = config.skill_ids || [];
    form.value.mcp_ids = config.mcp_ids || [];
    form.value.knowledge_base_ids = config.knowledge_base_ids || [];

    const advancedConfig = { ...config };
    delete advancedConfig.run_mode;
    delete advancedConfig.system_prompt;
    delete advancedConfig.custom_code;
    delete advancedConfig.tool_ids;
    delete advancedConfig.skill_ids;
    delete advancedConfig.mcp_ids;
    delete advancedConfig.knowledge_base_ids;
    delete advancedConfig.provider_connection_id;
    delete advancedConfig.engine_type;
    form.value.config_json = JSON.stringify(advancedConfig, null, 2);
    return;
  }

  if (isToolKind.value) {
    form.value.tool_runtime = config.runtime || "python";
    form.value.tool_entrypoint = config.entrypoint || "run";
    form.value.tool_shared = config.shared_in_project !== false;
    form.value.tool_code = config.code || "";
    form.value.tool_input_schema_json = JSON.stringify(config.input_schema || {}, null, 2);
    form.value.tool_output_schema_json = JSON.stringify(config.output_schema || {}, null, 2);

    form.value.model_provider = "";
    form.value.model_name = "";
    form.value.provider_profile = "";
    form.value.system_prompt = "";
    form.value.custom_code = "";
    form.value.tool_ids = [];
    form.value.skill_ids = [];
    form.value.mcp_ids = [];
    form.value.knowledge_base_ids = [];
    form.value.config_json = "{}";
    return;
  }


  if (isWorkflowKind.value) {
    form.value.model_provider = "";
    form.value.model_name = "";
    form.value.provider_profile = "";
    form.value.system_prompt = "";
    form.value.custom_code = "";
    form.value.tool_ids = [];
    form.value.skill_ids = [];
    form.value.mcp_ids = [];
    form.value.knowledge_base_ids = [];
    form.value.config_json = JSON.stringify(config, null, 2);
    loadWorkflowDraftFromDefinition(config);
    return;
  }

  if (isMcpKind.value) {
    form.value.mcp_transport = config.transport || "streamable_http";
    form.value.mcp_endpoint_url = config.endpoint_url || "";
    form.value.mcp_command = config.command || "";
    form.value.mcp_args_json = JSON.stringify(config.args || [], null, 2);
    form.value.mcp_headers_json = JSON.stringify(config.headers || {}, null, 2);
    form.value.mcp_env_json = JSON.stringify(config.env || {}, null, 2);
    form.value.mcp_timeout_seconds = String(config.timeout_seconds || 8);

    form.value.model_provider = "";
    form.value.model_name = "";
    form.value.provider_profile = "";
    form.value.system_prompt = "";
    form.value.custom_code = "";
    form.value.tool_ids = [];
    form.value.skill_ids = [];
    form.value.mcp_ids = [];
    form.value.knowledge_base_ids = [];

    const advancedConfig = { ...config };
    delete advancedConfig.transport;
    delete advancedConfig.endpoint_url;
    delete advancedConfig.command;
    delete advancedConfig.args;
    delete advancedConfig.headers;
    delete advancedConfig.env;
    delete advancedConfig.timeout_seconds;
    form.value.config_json = JSON.stringify(advancedConfig, null, 2);
    return;
  }

  form.value.model_provider = "";
  form.value.model_name = "";
  form.value.provider_profile = "";
  form.value.system_prompt = "";
  form.value.custom_code = "";
  form.value.tool_ids = [];
  form.value.skill_ids = [];
  form.value.mcp_ids = [];
  form.value.knowledge_base_ids = [];
  form.value.config_json = JSON.stringify(config, null, 2);
}

function applyTemplate() {
  if (!form.value.template_id) {
    return;
  }
  const template = templates.value.find((item) => item.template_id === form.value.template_id);
  if (!template) {
    return;
  }
  form.value.model_provider = template.model_provider || "";
  form.value.model_name = template.model_name || "";
  form.value.provider_profile = template.provider_profile || "";
  form.value.provider_connection_id = "";
  form.value.provider_config_mode = "env";
  form.value.provider_model_options = [];
  form.value.name = template.name;
  form.value.description = template.description || "";
}
async function handleProjectChange() {
  refreshAssociationOptions();
  form.value.provider_connection_id = "";
  form.value.provider_model_options = [];
  providerProbeResult.value = null;
  providerTestResult.value = null;
  await loadProviderConnections({ notify: true });
}

function refreshAssociationOptions() {
  form.value.tool_ids = form.value.tool_ids.filter((id) => toolOptions.value.some((item) => item.id === id));
  form.value.skill_ids = form.value.skill_ids.filter((id) => skillOptions.value.some((item) => item.id === id));
  form.value.mcp_ids = form.value.mcp_ids.filter((id) => mcpOptions.value.some((item) => item.id === id));
  form.value.knowledge_base_ids = form.value.knowledge_base_ids.filter((id) => kbOptions.value.some((item) => item.id === id));
}

function clearTest() {
  testMessages.value = [];
}

function parseAdvancedConfig() {
  const rawJson = form.value.config_json.trim();
  if (!rawJson) {
    return {};
  }
  try {
    return JSON.parse(rawJson);
  } catch {
    throw new Error("Advanced config JSON is invalid");
  }
}

function parseToolSchema(rawJson, label) {
  const text = (rawJson || "").trim();
  if (!text) {
    return {};
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`${label} is invalid JSON`);
  }
}

function parseJsonValue(rawText, label) {
  const text = (rawText || "").trim();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`${label} is invalid JSON`);
  }
}

function buildRuntimeConfig() {
  if (isToolKind.value) {
    const entrypoint = form.value.tool_entrypoint.trim();
    if (!entrypoint) {
      throw new Error("Tool function name is required");
    }
    return {
      runtime: form.value.tool_runtime,
      entrypoint,
      shared_in_project: !!form.value.tool_shared,
      code: form.value.tool_code,
      input_schema: parseToolSchema(form.value.tool_input_schema_json, "Tool input schema"),
      output_schema: parseToolSchema(form.value.tool_output_schema_json, "Tool output schema")
    };
  }
  if (isMcpKind.value) {
    if ((form.value.mcp_transport === "streamable_http" || form.value.mcp_transport === "sse") && !(form.value.mcp_endpoint_url || "").trim()) {
      throw new Error("MCP endpoint URL is required for streamable_http and sse transports");
    }
    if (form.value.mcp_transport === "stdio" && !(form.value.mcp_command || "").trim()) {
      throw new Error("MCP command is required for stdio transport");
    }
    const timeoutSeconds = Number(form.value.mcp_timeout_seconds || 8);
    const baseConfig = {
      transport: form.value.mcp_transport,
      endpoint_url: (form.value.mcp_transport === "streamable_http" || form.value.mcp_transport === "sse") ? (form.value.mcp_endpoint_url || "").trim() : "",
      command: form.value.mcp_transport === "stdio" ? (form.value.mcp_command || "").trim() : "",
      args: parseJsonValue(form.value.mcp_args_json, "MCP args") || [],
      headers: parseJsonValue(form.value.mcp_headers_json, "MCP headers") || {},
      env: parseJsonValue(form.value.mcp_env_json, "MCP env") || {},
      timeout_seconds: Number.isFinite(timeoutSeconds) && timeoutSeconds > 0 ? timeoutSeconds : 8
    };
    return {
      ...baseConfig,
      ...parseAdvancedConfig()
    };
  }
  if (isWorkflowKind.value) {
    const definition = buildWorkflowDefinitionFromCanvas();
    form.value.config_json = JSON.stringify(definition, null, 2);
    return definition;
  }
  if (!isAgentKind.value) {
    return parseAdvancedConfig();
  }
  const engine_type = (form.value.mcp_ids && form.value.mcp_ids.length > 0) ? "react" : "legacy";
  return {
    engine_type,
    run_mode: form.value.run_mode,
    system_prompt: form.value.system_prompt,
    provider_connection_id: form.value.provider_config_mode === "connection" ? (form.value.provider_connection_id || null) : null,
    custom_code: form.value.custom_code,
    tool_ids: form.value.tool_ids,
    skill_ids: form.value.skill_ids,
    mcp_ids: form.value.mcp_ids,
    knowledge_base_ids: form.value.knowledge_base_ids,
    ...parseAdvancedConfig()
  };
}
function buildProviderDraftPayload() {
  const baseUrl = (form.value.provider_base_url || "").trim();
  if (!baseUrl) {
    throw new Error("Provider Base URL is required");
  }
  return {
    provider_type: form.value.provider_type || "openai_compatible",
    base_url: baseUrl,
    api_key: form.value.provider_api_key || ""
  };
}

async function loadProviderModels() {
  if (!isAgentKind.value) {
    return;
  }
  if (!form.value.project_id) {
    Message.warning("Please select project first");
    return;
  }
  let payload;
  try {
    payload = buildProviderDraftPayload();
  } catch (error) {
    Message.error(error.message || "Provider config invalid");
    return;
  }
  providerLoadingModels.value = true;
  providerProbeResult.value = null;
  try {
    const result = await api.probeProviderModels(form.value.project_id, payload);
    providerProbeResult.value = result;
    if (result.ok) {
      form.value.provider_model_options = result.models || [];
      if (!form.value.model_name && form.value.provider_model_options.length > 0) {
        form.value.model_name = form.value.provider_model_options[0];
      }
      Message.success(`Loaded ${form.value.provider_model_options.length} models`);
    } else {
      Message.error(result.error || "Load models failed; you can enter model name manually");
    }
  } catch (error) {
    Message.error(error.message || "Load models failed");
  } finally {
    providerLoadingModels.value = false;
  }
}

async function testProviderDraft() {
  if (!form.value.project_id) {
    Message.warning("Please select project first");
    return;
  }
  if (!form.value.model_name) {
    Message.warning("Please select or enter model name first");
    return;
  }
  let payload;
  try {
    payload = {
      ...buildProviderDraftPayload(),
      model_name: form.value.model_name,
      text: "ping"
    };
  } catch (error) {
    Message.error(error.message || "Provider config invalid");
    return;
  }
  providerTesting.value = true;
  providerTestResult.value = null;
  try {
    const result = await api.testProviderConnectionDraft(form.value.project_id, payload);
    providerTestResult.value = result;
    if (result.ok) {
      Message.success("Provider test success");
    } else {
      Message.error(result.error || "Provider test failed");
    }
  } catch (error) {
    Message.error(error.message || "Provider test failed");
  } finally {
    providerTesting.value = false;
  }
}

async function saveProviderConnectionDraft() {
  if (!form.value.project_id) {
    Message.warning("Please select project first");
    return;
  }
  if (!form.value.provider_connection_name.trim()) {
    Message.warning("Provider connection name is required");
    return;
  }
  if (!form.value.model_name) {
    Message.warning("Please select or enter model name first");
    return;
  }
  let draft;
  try {
    draft = buildProviderDraftPayload();
  } catch (error) {
    Message.error(error.message || "Provider config invalid");
    return;
  }
  providerSaving.value = true;
  try {
    const saved = await api.createProviderConnection(form.value.project_id, {
      name: form.value.provider_connection_name.trim(),
      provider_type: draft.provider_type,
      base_url: draft.base_url,
      api_key: draft.api_key,
      default_model: form.value.model_name,
      model_list_cache: form.value.provider_model_options || []
    });
    await loadProviderConnections({ notify: true });
    form.value.provider_connection_id = saved.id;
    form.value.provider_config_mode = "connection";
    form.value.provider_api_key = "";
    Message.success("Provider connection saved and selected");
  } catch (error) {
    Message.error(error.message || "Save provider connection failed");
  } finally {
    providerSaving.value = false;
  }
}

function applyProviderConnection() {
  const selected = selectedProviderConnection.value;
  if (!selected) {
    form.value.provider_model_options = [];
    return;
  }
  form.value.provider_type = selected.provider_type || "openai_compatible";
  form.value.provider_base_url = selected.base_url || "";
  form.value.provider_model_options = selected.model_list_cache || [];
  if (!form.value.model_name && selected.default_model) {
    form.value.model_name = selected.default_model;
  }
}

async function probeMcpDraft() {
  if (!isMcpKind.value) {
    return;
  }
  if (!form.value.project_id) {
    Message.warning("Please select project first");
    return;
  }

  let config;
  try {
    config = buildRuntimeConfig();
  } catch (error) {
    Message.error(error.message || "MCP config invalid");
    return;
  }

  mcpProbing.value = true;
  mcpProbeResult.value = null;
  try {
    const result = await api.probeMcp({
      project_id: form.value.project_id,
      config
    });
    mcpProbeResult.value = result;
    if (result.ok) {
      Message.success("MCP probe success");
    } else {
      Message.error(result.error || "MCP probe failed");
    }
  } catch (error) {
    Message.error(error.message || "MCP probe failed");
  } finally {
    mcpProbing.value = false;
  }
}

function copyMcpTemplate() {
  // Copy recommended template values to form
  form.value.mcp_headers_json = mcpTemplateHeaders;
  form.value.mcp_env_json = mcpTemplateEnv;
  form.value.config_json = mcpTemplateAdvanced;
  showMcpTemplate.value = false;
  Message.success("Template copied to form! Edit as needed.");
}

async function runDraftTest() {
  if (!isAgentKind.value) {
    Message.warning("Draft chat test is available for agent resources only");
    return;
  }
  const text = testInput.value.trim();
  if (!form.value.project_id) {
    Message.warning("Please select project first");
    return;
  }
  if (!text) {
    Message.warning("Please input test message");
    return;
  }

  testing.value = true;
  testMessages.value.push({ role: "user", text });
  testInput.value = "";
  try {
    const runtimeConfig = buildRuntimeConfig();
    const result = await api.previewResourceChat({
      project_id: form.value.project_id,
      text,
      run_mode: form.value.run_mode,
      model_provider: form.value.model_provider || null,
      model_name: form.value.model_name || null,
      provider_profile: form.value.provider_config_mode === "env" ? (form.value.provider_profile || null) : null,
      provider_connection_id: form.value.provider_config_mode === "connection" ? (form.value.provider_connection_id || null) : null,
      system_prompt: form.value.system_prompt || null,
      custom_code: form.value.custom_code,
      config: runtimeConfig
    });
    testMessages.value.push({ role: "assistant", text: result.text || "" });
  } catch (error) {
    const textError = error.message || "Preview failed";
    testMessages.value.push({ role: "assistant", text: `[error] ${textError}` });
    Message.error(textError);
  } finally {
    testing.value = false;
  }
}

async function submitForm() {
  if (!form.value.project_id) {
    Message.warning("Please select project");
    return;
  }
  const name = form.value.name.trim();
  if (name.length < 2) {
    Message.warning("Resource name requires at least 2 chars");
    return;
  }

  if (isAgentKind.value && form.value.model_mode === "default") {
    if (!form.value.template_id) {
      Message.warning("Please select a template or switch to custom model settings");
      return;
    }
  }

  if (isAgentKind.value && form.value.model_mode === "custom" && form.value.provider_config_mode === "connection") {
    if (!form.value.provider_connection_id) {
      Message.warning("Please save or select a provider connection first");
      return;
    }
  }

  saving.value = true;
  try {
    const config = buildRuntimeConfig();
    const payload = {
      kind: kind.value,
      name,
      visibility: form.value.visibility,
      description: form.value.description,
      model_provider: isAgentKind.value ? (form.value.model_provider || null) : null,
      model_name: isAgentKind.value ? (form.value.model_name || null) : null,
      provider_profile: isAgentKind.value && form.value.provider_config_mode === "env" ? (form.value.provider_profile || null) : null,
      provider_connection_id: isAgentKind.value && form.value.provider_config_mode === "connection" ? (form.value.provider_connection_id || null) : null,
      config
    };
    let createdResourceId = null;
    if (isEditMode.value && resourceId.value) {
      await api.updateResource(resourceId.value, { ...payload, project_id: form.value.project_id });
      Message.success(`${kind.value} updated`);
      goBack();
    } else {
      const result = await api.createResource(form.value.project_id, payload);
      createdResourceId = result.id;
      Message.success(`${kind.value} created`);
      // Navigate to documents page for Knowledge Base
      if (isKnowledgeKind.value && createdResourceId) {
        setTimeout(() => {
          router.push({ name: "resources-knowledge-bases-detail", params: { resourceId: createdResourceId } });
        }, 1000);
      } else if (isSkillKind.value && createdResourceId) {
        setTimeout(() => {
          router.push({ name: "resources-skill-detail", params: { resourceId: createdResourceId } });
        }, 1000);
      } else {
        goBack();
      }
    }
  } catch (error) {
    Message.error(error.message || `${isEditMode.value ? "Update" : "Create"} resource failed`);
  } finally {
    saving.value = false;
  }
}


watch(
  [workflowDraft, workflowNodes, workflowEdges, workflowOutputJson],
  () => {
    updateWorkflowJsonFromCanvas();
  },
  { deep: true }
);
watch(
  () => isWorkflowKind.value,
  (active) => {
    if (active) {
      requestWorkflowFitView();
    }
  }
);
onMounted(async () => {
  try {
    applyCreateDefaultsByKind();
    await Promise.all([loadProjects(), loadTemplates(), loadOwnedResources()]);
    await loadProviderConnections({ notify: true });
    await loadResource();
    await loadProviderConnections({ notify: true });
  } catch (error) {
    Message.error(error.message || "Load create form data failed");
  }
});
</script>

<style scoped>
.chat-test-card {
  min-height: 780px;
}

.chat-messages {
  border: 1px solid #dcdee2;
  border-radius: 8px;
  padding: 8px;
  margin: 12px 0;
  height: 420px;
  overflow-y: auto;
  background: #fafafa;
}

.chat-empty {
  color: #808695;
  text-align: center;
  margin-top: 180px;
}

.chat-message {
  margin-bottom: 8px;
  padding: 8px;
  border-radius: 6px;
  background: #fff;
}

.chat-message.role-user {
  border-left: 3px solid #2d8cf0;
}

.chat-message.role-assistant {
  border-left: 3px solid #19be6b;
}

.chat-role {
  font-size: 12px;
  color: #808695;
  margin-bottom: 4px;
}

.chat-text {
  white-space: pre-wrap;
  word-break: break-word;
}

.authoring-guide-alert {
  margin-bottom: 16px;
}

.authoring-guide-copy {
  display: grid;
  gap: 8px;
  line-height: 1.6;
}

.authoring-guide-copy a {
  margin-left: 6px;
  color: #0f6fb8;
  font-weight: 600;
}

.config-example-block {
  margin: 0;
  padding: 10px 12px;
  border-radius: 6px;
  background: #f8f9fb;
  border: 1px solid #e8eaec;
  font-family: Consolas, "Courier New", monospace;
  white-space: pre-wrap;
  overflow-x: auto;
}

.workflow-builder {
  margin: 22px 0;
  padding: 22px;
  border: 1px solid #d5e2f0;
  border-radius: 14px;
  background: linear-gradient(180deg, #f7fbff 0%, #eef6ff 48%, #ffffff 100%);
  box-shadow: 0 18px 48px rgba(20, 38, 70, 0.10);
}

.workflow-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
  margin-bottom: 18px;
  padding-bottom: 16px;
  border-bottom: 1px solid #dce8f4;
}

.workflow-toolbar h3 {
  margin: 0;
  font-size: 24px;
  color: #111c31;
  letter-spacing: 0;
}

.workflow-toolbar p {
  margin: 7px 0 0;
  color: #607089;
}

.workflow-meta-row {
  margin-bottom: 10px;
  padding: 14px 14px 0;
  border: 1px solid #dbe7f3;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.82);
}

.workflow-canvas {
  padding: 16px;
  border: 1px solid #d5e2f0;
  border-radius: 16px;
  background: linear-gradient(135deg, #f6f9fd 0%, #eef6ff 100%);
}

.split-canvas {
  display: grid;
  grid-template-columns: minmax(720px, 1fr) minmax(340px, 390px);
  gap: 18px;
  align-items: start;
}

.workflow-flow-panel,
.workflow-editor-panel {
  border: 1px solid #d7e3f0;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 18px 42px rgba(31, 51, 79, 0.10);
}

.workflow-flow-panel {
  padding: 16px;
}

.workflow-editor-panel {
  padding: 18px;
}

.flow-panel-title,
.editor-panel-heading {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-bottom: 14px;
}

.flow-panel-title span {
  color: #162238;
  font-weight: 800;
}

.editor-panel-heading h3 {
  margin: 6px 0 0;
  color: #162238;
  font-size: 20px;
}

.flow-start,
.flow-end {
  width: fit-content;
  min-width: 92px;
  margin: 0 auto;
  padding: 8px 14px;
  border-radius: 999px;
  text-align: center;
  font-weight: 800;
}

.flow-start {
  color: #075985;
  background: #e0f2fe;
}

.flow-end {
  color: #166534;
  background: #dcfce7;
}

.flow-node-wrap {
  display: grid;
  justify-items: stretch;
}

.flow-connector {
  display: grid;
  place-items: center;
  height: 28px;
}

.flow-connector span {
  width: 2px;
  height: 100%;
  border-radius: 99px;
  background: #9fb5ce;
}

.flow-node {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  width: 100%;
  min-height: 72px;
  padding: 12px;
  border: 1px solid #d7e3f0;
  border-radius: 10px;
  background: #ffffff;
  color: #1f2d3d;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.16s ease, box-shadow 0.16s ease, transform 0.16s ease;
}

.flow-node:hover,
.flow-node.active {
  border-color: #0f766e;
  box-shadow: 0 12px 30px rgba(15, 118, 110, 0.14);
  transform: translateY(-1px);
}

.flow-node.active {
  background: #f0fdfa;
}

.flow-node-index {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 999px;
  background: #0f766e;
  color: #ffffff;
  font-weight: 800;
}

.flow-node-copy {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.flow-node-copy strong,
.flow-node-copy small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.flow-node-copy strong {
  color: #162238;
}

.flow-node-copy small {
  color: #64748b;
}

.flow-node-mode {
  padding: 4px 8px;
  border-radius: 999px;
  background: #eef4fb;
  color: #475569;
  font-size: 12px;
  font-weight: 800;
}
.workflow-fullscreen-overlay {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: grid;
  padding: 14px;
  background: rgba(11, 18, 32, 0.82);
  backdrop-filter: blur(10px);
}

.workflow-fullscreen-shell {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 12px;
  height: 100%;
  border: 1px solid rgba(219, 231, 243, 0.45);
  border-radius: 16px;
  background: #f6f9fd;
  box-shadow: 0 30px 90px rgba(0, 0, 0, 0.32);
  overflow: hidden;
}

.workflow-fullscreen-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid #dbe7f3;
  background: #ffffff;
}

.workflow-fullscreen-toolbar h3 {
  margin: 0;
  color: #162238;
}

.workflow-fullscreen-toolbar p {
  margin: 4px 0 0;
  color: #64748b;
}
.workflow-vue-flow {
  width: 100%;
  height: 700px;
  border: 1px solid #dce8f4;
  border-radius: 12px;
  background: #f7fbff;
  overflow: hidden;
}

.flow-card-node {
  display: grid;
  gap: 8px;
  min-width: 250px;
  padding: 14px;
  border: 1px solid #d7e3f0;
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 14px 34px rgba(31, 51, 79, 0.14);
}

.workflow-vue-node.selected .flow-card-node,
.vue-flow__node.selected .flow-card-node {
  display: grid;
  gap: 8px;
  min-width: 250px;
  padding: 14px;
  border: 1px solid #d7e3f0;
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 14px 34px rgba(31, 51, 79, 0.14);
}

.flow-card-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
}

.flow-card-head strong {
  color: #162238;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.flow-card-head span {
  padding: 3px 8px;
  border-radius: 999px;
  background: #eef4fb;
  color: #475569;
  font-size: 12px;
  font-weight: 800;
}

.workflow-vue-flow.fullscreen {
  height: 100%;
}

.flow-card-node small {
  color: #64748b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.connection-editor {
  margin: 14px 0 18px;
  padding: 14px;
  border: 1px solid #dbe7f3;
  border-radius: 12px;
  background: #f8fbff;
}

.connection-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 12px;
}

.connection-header strong {
  color: #162238;
}

.connection-header span,
.connection-empty {
  color: #64748b;
  font-size: 12px;
}

.connection-groups {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.connection-groups small {
  display: block;
  margin-bottom: 8px;
  color: #52627a;
  font-weight: 700;
}

.connection-tags {
  min-height: 30px;
}

.edge-list {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}

.edge-row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
  padding: 8px 10px;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid #e2eaf3;
  color: #334155;
}

.edge-row span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
@media (max-width: 900px) {
  .workflow-toolbar,
  .editor-panel-heading,
  .routing-row {
    align-items: stretch;
    flex-direction: column;
  }

  .split-canvas {
    grid-template-columns: 1fr;
  }

  .route-mode-select {
    width: 100%;
    flex-basis: auto;
  }
}
.mcp-template-modal {
  max-height: 600px;
  overflow-y: auto;
  padding: 8px 0;
}

.template-section {
  margin-bottom: 20px;
}

.template-section h4 {
  margin: 0 0 8px 0;
  color: #1f2d3d;
  font-size: 14px;
  font-weight: 600;
}

.template-code {
  background: #f8f9fb;
  border: 1px solid #e8eaec;
  border-radius: 6px;
  padding: 12px;
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
  line-height: 1.6;
}

.code-line {
  margin: 4px 0;
}

.code-line .key {
  color: #c41d7f;
  font-weight: 600;
}

.code-line .value {
  color: #135200;
}

.template-json {
  margin: 8px 0;
  padding: 10px 12px;
  background: #f8f9fb;
  border: 1px solid #e8eaec;
  border-radius: 6px;
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
  line-height: 1.5;
  overflow-x: auto;
}

.template-hint {
  margin: 8px 0 0 0;
  color: #666;
  font-size: 12px;
}
</style>
