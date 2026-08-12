$ErrorActionPreference = 'Stop'

$apiKey = [Environment]::GetEnvironmentVariable('LINEAR_API_KEY', 'User')
if ([string]::IsNullOrWhiteSpace($apiKey)) {
    Write-Output 'KEY_MISSING'
    exit 2
}

$endpoint = 'https://api.linear.app/graphql'

function Invoke-LinearGraphQL {
    param(
        [Parameter(Mandatory = $true)][string]$Query,
        [Parameter(Mandatory = $true)][hashtable]$Variables
    )

    $payload = @{ query = $Query; variables = $Variables } | ConvertTo-Json -Depth 20 -Compress
    $body = [Text.Encoding]::UTF8.GetBytes($payload)
    $response = Invoke-RestMethod -Uri $endpoint -Method Post -Headers @{ Authorization = $apiKey } -ContentType 'application/json; charset=utf-8' -Body $body
    if ($response.errors) {
        throw (($response.errors | ForEach-Object { $_.message }) -join '; ')
    }
    return $response.data
}

$issueQuery = @'
query IssueByIdentifier($id: String!) {
  issue(id: $id) {
    id
    identifier
    title
    state { id name type }
    team { id states { nodes { id name type } } }
    comments { nodes { id body } }
  }
}
'@

$updateMutation = @'
mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
  issueUpdate(id: $id, input: $input) {
    success
    issue { identifier state { name type } }
  }
}
'@

$commentMutation = @'
mutation CreateComment($input: CommentCreateInput!) {
  commentCreate(input: $input) { success comment { id } }
}
'@

$marker = '[JITSI-SYNC-2026-08-12]'
$comments = @{
    'ZZJ-23' = "$marker 评估完成：采用自建 Jitsi Meet（Docker Compose），通过 Mattermost Jitsi 插件接入；会议入口为 https://meet.rongsunai.com，启用 HTTPS 和主持人认证。"
    'ZZJ-24' = "$marker 部署验收完成：Jitsi stable-10978 已通过 Docker Compose 部署；HTTPS 正常；云安全组已放行 JVB UDP 10000；电脑端与手机端联合测试稳定。"
    'ZZJ-25' = "$marker 验证完成：Mattermost 中使用 /jitsi start 可生成会议链接；主持人登录及电脑、手机双端入会正常。此前断线由 UDP 10000 未放行导致，补充安全组规则后复测正常。"
    'ZZJ-26' = "$marker 保持 Todo：DocSpace / ONLYOFFICE 编辑器内嵌 Jitsi 属于后续扩展，不纳入本次 Mattermost 集成验收。"
}

foreach ($identifier in @('ZZJ-23', 'ZZJ-24', 'ZZJ-25', 'ZZJ-26')) {
    $issue = (Invoke-LinearGraphQL -Query $issueQuery -Variables @{ id = $identifier }).issue
    if (-not $issue) { throw "Issue not found: $identifier" }

    $targetType = if ($identifier -eq 'ZZJ-26') { 'unstarted' } else { 'completed' }
    $targetState = $issue.team.states.nodes | Where-Object { $_.type -eq $targetType } | Select-Object -First 1
    if (-not $targetState) { throw "No $targetType state found for $identifier" }

    if ($issue.state.id -ne $targetState.id) {
        $updated = Invoke-LinearGraphQL -Query $updateMutation -Variables @{
            id = $issue.id
            input = @{ stateId = $targetState.id }
        }
        if (-not $updated.issueUpdate.success) { throw "Failed to update $identifier" }
    }

    $alreadyCommented = $issue.comments.nodes | Where-Object { $_.body -like "$marker*" } | Select-Object -First 1
    if (-not $alreadyCommented) {
        $created = Invoke-LinearGraphQL -Query $commentMutation -Variables @{
            input = @{ issueId = $issue.id; body = $comments[$identifier] }
        }
        if (-not $created.commentCreate.success) { throw "Failed to comment on $identifier" }
    }
}

$results = foreach ($identifier in @('ZZJ-23', 'ZZJ-24', 'ZZJ-25', 'ZZJ-26')) {
    $issue = (Invoke-LinearGraphQL -Query $issueQuery -Variables @{ id = $identifier }).issue
    "$identifier=$($issue.state.name)"
}
Write-Output ($results -join ';')
