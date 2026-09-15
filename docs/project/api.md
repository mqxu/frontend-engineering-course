# 接口约定

这一页是前后端的**接口合同**。定下来之后双方都照着它写，谁改都要通知对方。

**这份文档是沟通工具，不是前端单方面的产出。** 里面每一条约定，都应该是和后端同学对过之后写下来的。

## 一、基础约定

| 项 | 值 |
| --- | --- |
| 基础路径 | `/api` |
| 数据格式 | JSON（`Content-Type: application/json`） |
| 字符编码 | UTF-8 |
| 鉴权方式 | 请求头 `Authorization: Bearer <token>` |
| 时间格式 | 字符串，`yyyy-MM-dd HH:mm:ss`，**不带时区** |

**基础路径在开发和生产环境不同：**

| 环境 | 前端配置 | 实际请求地址 |
| --- | --- | --- |
| 开发 | `VITE_API_BASE_URL=/api` + Vite 代理 | `http://localhost:5173/api/...` → 转发到 `localhost:8080` |
| 生产 | `VITE_API_BASE_URL=/api` + Nginx 转发 | `https://activity.example.edu.cn/api/...` → 转发到 `127.0.0.1:8080` |

**两个环境都用 `/api`**，因为都是“同域 + 服务端转发”，前端代码不用改。

## 二、统一响应结构

所有接口——包括成功的和失败的——都返回这个结构：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `code` | number | 业务状态码。`0` 表示成功，非 `0` 表示业务失败 |
| `message` | string | 给用户看的提示文案 |
| `data` | any | 业务数据。失败时为 `null` |

### 为什么要有业务码

HTTP 状态码不够用。举例：

- “用户名或密码错误”和“账号被禁用”都是 401
- “活动不存在”和“活动已结束不能编辑”都是 400

前端要区分这些情况（提示文案不同、后续动作不同），就需要业务码。

### 成功响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 42,
    "title": "2026 春季校园歌手大赛",
    "status": "SIGNING"
  }
}
```

### 失败响应示例

```json
{
  "code": 2001,
  "message": "活动不存在或已被删除",
  "data": null
}
```

::: warning 需要和后端确认的一件事：失败时 HTTP 状态码是什么
两种约定都存在：

| 约定 | HTTP 状态码 | 前端拦截器怎么写 |
| --- | --- | --- |
| A · 一律 200 | 失败也返回 200，靠 `code` 区分 | 在成功回调里判断 `code !== 0` |
| B · 用 4xx | 业务失败返回 4xx，进入错误回调 | 在错误回调里读 `response.data.code` |

**这两种的拦截器写法完全不同。** 定下来之后写进这份文档，不要中途改。

**课程项目推荐约定 A**，因为逻辑集中在一处，不用在两个回调里都处理业务码。但如果后端框架（比如 Spring Security）默认返回 401 / 403，混用也是可以的 —— **那就把“哪些情况返回 4xx”列清楚。**
:::

## 三、错误码表

| 码 | HTTP | 含义 | 前端该怎么处理 |
| --- | --- | --- | --- |
| `0` | 200 | 成功 | — |
| `1001` | 401 | 未登录，或 token 失效 | 清理登录态，跳登录页 |
| `1002` | 403 | 已登录但无权限 | 提示“没有权限执行此操作” |
| `1003` | 400 | 参数校验失败 | 显示后端返回的 `message` |
| `1004` | 404 | 资源不存在 | 提示并返回列表页 |
| `2001` | 400 | 活动不存在 | 返回活动列表 |
| `2002` | 400 | 活动状态不允许此操作 | 提示具体原因，刷新列表 |
| `2003` | 400 | 名额不能小于已通过人数 | 在表单字段下显示错误 |
| `2004` | 400 | 报名截止时间必须晚于当前时间 | 在表单字段下显示错误 |
| `2005` | 400 | 名额已满 | 提示并用红字显示名额 |
| `2006` | 400 | 已过报名截止时间 | 提示并返回活动列表 |
| `2007` | 400 | 当前状态不可报名 | 提示活动状态，刷新详情 |
| `3001` | 400 | 报名记录不存在 | 返回报名列表 |
| `3002` | 400 | 报名状态不允许此操作 | 提示并刷新列表 |
| `3003` | 400 | 驳回理由不能为空 | 在驳回对话框中显示错误 |
| `3004` | 400 | 已报名该活动 | 提示并跳到“我的报名” |
| `4001` | 400 | 场地或场次不存在 | 提示并返回列表页 |
| `4002` | 400 | 场地名称已存在 | 在表单字段下显示错误 |
| `4003` | 400 | 场次时段与已有场次冲突 | 提示冲突的场次信息 |
| `4004` | 400 | 场次时间范围不合法 | 在表单字段下显示错误 |
| `4005` | 400 | 场次状态不允许此操作 | 提示并刷新列表 |
| `5000` | 500 | 服务器内部错误 | 提示“服务器异常，请稍后重试” |

**三条使用规则：**

**规则一：前端不要按 `message` 做判断，要按 `code`。**

`message` 是给用户看的，随时可能改文案。`code` 才是稳定的契约。

```js
// ✗ 文案一改就失效
if (res.message === '名额已满') { /* ... */ }

// ✓
if (res.code === 2005) { /* ... */ }
```

**规则二：`4003` 冲突要比普通错误处理得更细。**

普通错误提示一句就够了。但冲突要告诉用户**和哪个场次冲突**：

```js
if (err.code === 4003) {
  const conflict = err.data          // 后端返回冲突的场次信息
  ElMessage.error(`与“${conflict.activityTitle}”${conflict.startTime} 的场次冲突`)
  // 并把冲突的场次在时间轴或列表里高亮出来
}
```

**这要求后端在 4003 的响应里带回冲突场次的信息。** 这一条要提前和后端说，否则他只会返回一句“时段冲突”。

**规则三：`2003`、`2004`、`4002`、`4004` 是表单字段级错误，不是全局提示。**

这四个错误对应具体的表单字段，应该显示在字段下方，而不是弹一个全局的提示框。

```js
if (err.code === 2003) {
  // 在 quota 字段下显示错误
  quotaError.value = err.message
}
```

## 四、分页约定

### 请求参数

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `page` | number | `1` | 页码，从 1 开始 |
| `pageSize` | number | `10` | 每页条数，可选值 10 / 20 / 50 |
| `keyword` | string | — | 关键字搜索，按业务决定搜索哪些字段 |
| `sortBy` | string | — | 排序字段名 |
| `sortOrder` | string | `desc` | `asc` 或 `desc` |

**`page` 从 1 开始**，不是从 0。这一点要写清楚 —— 有些后端默认从 0 开始，前端传 1 会跳过第一页。

### 响应结构

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "list": [],
    "total": 42,
    "page": 1,
    "pageSize": 10
  }
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `list` | array | 当前页的数据 |
| `total` | number | **总条数**，不是当前页条数 |
| `page` | number | 当前页码 |
| `pageSize` | number | 每页条数 |

**前端只用 `list` 和 `total`。** `page` 和 `pageSize` 由前端自己维护，后端返回它们是方便排查问题。

::: warning `total` 必须是总条数
前端分页器的页码数靠 `total` 算出来的：`Math.ceil(total / pageSize)`。

如果后端返回的是当前页数组的长度，分页器永远只有一页。**这是联调时最常见的 bug 之一。**

前端能做的检查：列表里明明有 10 条数据，分页器显示“共 0 条”，就是这个问题。
:::

## 五、登录鉴权接口

### 登录

```
POST /api/auth/login
```

**请求体**

```json
{
  "username": "organizer",
  "password": "******"
}
```

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "token": "<token 字符串>",
    "expiresIn": 7200,
    "userInfo": {
      "id": 1,
      "username": "organizer",
      "realName": "李组织",
      "role": "ORGANIZER"
    }
  }
}
```

| 字段 | 说明 |
| --- | --- |
| `token` | 访问令牌。前端存到 `localStorage`，后续请求放在 `Authorization` 头里 |
| `expiresIn` | token 有效期，单位秒。前端可以用它判断是否需要提前续期 |
| `userInfo.role` | `ORGANIZER`（组织者）或 `AUDITOR`（审核员） |

**错误情况**

| 码 | 场景 |
| --- | --- |
| `1001` | 用户名或密码错误 |
| `1005` | 账号已被禁用 |

### 获取当前用户

```
GET /api/auth/me
```

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "username": "organizer",
    "realName": "李组织",
    "role": "ORGANIZER",
    "department": "校学生会"
  }
}
```

**这个接口的用处**：刷新页面时用 token 换回用户信息，恢复登录态。**没有它的话，刷新页面后只有 token，不知道当前用户是谁、什么角色。**

### 退出登录

```
POST /api/auth/logout
```

**响应**

```json
{ "code": 0, "message": "success", "data": null }
```

**前端要做的**：无论这个接口成功还是失败，都要清掉本地的 token 和用户信息。

```js
async function logout() {
  try {
    await logoutApi()
  } catch {
    // 忽略错误：即使后端失败，本地也必须清干净
  } finally {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('access_token')
    router.push('/login')
  }
}
```

## 六、活动管理接口

### 活动列表

```
GET /api/activities
```

**查询参数**

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `keyword` | string | 按活动标题模糊搜索 |
| `status` | string | `DRAFT` / `SIGNING` / `SIGNUP_CLOSED` / `FINISHED` |
| `offShelf` | boolean | 是否只看已下架的 |
| `page` / `pageSize` | number | 分页 |

**响应中的单条活动对象**

```json
{
  "id": 42,
  "title": "2026 春季校园歌手大赛",
  "type": "COMPETITION",
  "typeName": "比赛竞赛",
  "organizerId": 1,
  "organizerName": "李组织",
  "quota": 100,
  "approvedCount": 42,
  "pendingCount": 8,
  "signupDeadline": "2026-04-01 18:00:00",
  "status": "SIGNING",
  "statusName": "报名中",
  "offShelf": false,
  "description": "面向全校本科生…",
  "createdAt": "2026-03-15 10:20:30",
  "updatedAt": "2026-03-18 09:05:12",
  "canEdit": true,
  "canDelete": false,
  "canOffShelf": true
}
```

**注意 `canEdit` / `canDelete` / `canOffShelf` 三个字段。** 列表接口和详情接口**都要返回**，因为列表页的操作列按钮也要按这三个值显隐。

**只让详情接口返回是不行的** —— 那样列表页每行都得再查一次详情，一页 20 条就是 20 次请求。**这类权限布尔值要让所有返回活动对象的接口都带上。**

**注意两个字段：**

| 字段 | 为什么需要 |
| --- | --- |
| `typeName` / `statusName` | 后端返回中文文案，前端不用自己维护字典。**但如果同一个状态在不同页面的文案不同（列表用“报名中”、看板用“进行中”），就要前端自己维护** —— 这时候告知后端不用返回 |
| `approvedCount` / `pendingCount` | 由后端维护，前端只读。见[业务规则](/project/rules)里的并发说明 |

**权限**：组织者只能看到 `organizerId` 是自己的活动。**这个过滤在后端做，前端不传 `organizerId`。**

**为什么不传**：如果前端传 `organizerId`，那么改一下参数就能看到别人的活动 —— 这等于没有权限控制。**后端应该根据 token 里的用户身份自动过滤。**

### 活动详情

```
GET /api/activities/:id
```

**响应**：同列表中的单条对象，另加：

```json
{
  "approvedCount": 42,
  "pendingCount": 8,
  "rejectedCount": 3,
  "sessionCount": 3
}
```

**这五个统计数字由后端算好返回，前端不要自己用“查列表然后数长度”的方式算** —— 列表接口只返回当前页的数据，数出来的永远是第一页的数量。

### 三个权限布尔值的取舍

列表和详情返回的 `canEdit` / `canDelete` / `canOffShelf`，是一个值得讲的设计选择。

| 做法 | 好处 | 代价 |
| --- | --- | --- |
| 后端返回这三个布尔值 | 规则只有一份，前后端不会不一致 | 每个需要权限控制的接口都要加这几个字段 |
| 前端自己算 | 后端接口简单 | 规则要写两遍，容易不一致 |

**课程项目推荐后端返回。** 因为[业务规则](/project/rules)里的判断条件不少（状态、下架、名额、角色），前端自己算容易漏。

**但前端仍要知道规则的内容** —— 因为要写测试、要解释给用户听、要在别的页面做类似判断。**“前端不算”不等于“前端不用懂”。**

### 新增活动

```
POST /api/activities
```

**请求体**

```json
{
  "title": "2026 春季校园歌手大赛",
  "type": "COMPETITION",
  "quota": 100,
  "signupDeadline": "2026-04-01 18:00:00",
  "description": "面向全校本科生…"
}
```

**注意**：请求体里**不包含 `status`、`offShelf`、`approvedCount`**。这些由后端决定：

- 新建的活动 `status = 'DRAFT'`、`offShelf = false`
- `approvedCount` 和 `pendingCount` 初始为 0

**响应**

```json
{ "code": 0, "message": "success", "data": { "id": 42 } }
```

**创建并发布**是一个动作还是两个？

| 做法 | 接口设计 |
| --- | --- |
| 一个接口 | `POST /api/activities` 带 `publish: true` 参数，后端在一个事务里创建 + 发布 |
| 两个接口 | 先 `POST` 创建拿到 id，再 `PATCH /api/activities/:id/publish` |

**推荐一个接口。** 两个接口的问题是不是原子的 —— 第二个失败时活动已经创建了，用户看到“发布失败”但列表里已经有这条记录。见 [11.5 表单页标准做法](/unit11/05-form-page)里的讨论。

### 编辑活动

```
PUT /api/activities/:id
```

**请求体**：与新增相同，另加按状态限制的字段。

**限制**（见[业务规则](/project/rules)）：

- `SIGNING` 状态下，`quota` 只能调大，`signupDeadline` 只能往后推
- `FINISHED` 状态下，所有字段只读

**后端必须在事务里校验这些限制**，不能只靠前端禁用输入框。

**错误**

| 码 | 场景 |
| --- | --- |
| `2002` | 状态不允许编辑 |
| `2003` | 名额小于已通过人数 |
| `2004` | 截止时间不在未来 |

### 发布活动

```
PATCH /api/activities/:id/status
```

**请求体**

```json
{ "status": "SIGNING" }
```

**为什么用 PATCH 不用 PUT**：这只是改一个字段，不是替换整个活动对象。语义上 `PATCH` 更准确。

**允许的转换**：只有 `DRAFT → SIGNING`。其他转换由系统按时间自动完成，接口不接受。

**错误**

| 码 | 场景 |
| --- | --- |
| `2002` | 当前状态不是 `DRAFT` |
| `2004` | 报名截止时间已过，不能发布 |

**最后一条不能漏**：一个活动创建了三个月，报名截止时间早就过了。这时候发布，学生点进去发现报名已经截止，体验很差。**发布前要校验截止时间还在未来。**

### 下架 / 恢复上架

```
PATCH /api/activities/:id/offshelf
```

**请求体**

```json
{ "offShelf": true }
```

**响应**：`{ "code": 0, "message": "success", "data": null }`

**错误**

| 码 | 场景 |
| --- | --- |
| `2002` | `DRAFT` 或 `FINISHED` 状态不能下架 |

### 删除活动

```
DELETE /api/activities/:id
```

**只有 `DRAFT` 状态的活动能删除。** 其他状态返回 `2002`。

**响应**：`{ "code": 0, "message": "success", "data": null }`

## 七、报名审核接口

### 报名列表

```
GET /api/signups
```

**查询参数**

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `activityId` | number | 按活动筛选 |
| `status` | string | `PENDING` / `APPROVED` / `REJECTED` / `CANCELLED` |
| `keyword` | string | 按学生姓名或学号搜索 |
| `page` / `pageSize` | number | 分页 |

**权限**：组织者只能看到自己活动下的报名。审核员能看全部。

**响应中的单条报名对象**

```json
{
  "id": 301,
  "activityId": 42,
  "activityTitle": "2026 春季校园歌手大赛",
  "studentId": 1088,
  "studentName": "王小明",
  "studentNo": "2023010108",
  "studentClass": "软件 2301",
  "status": "PENDING",
  "statusName": "待审核",
  "remark": "曾获校级歌唱比赛二等奖",
  "rejectReason": null,
  "createdAt": "2026-03-16 14:22:10",
  "auditedAt": null,
  "auditorName": null
}
```

**注意 `activityTitle` 和 `studentName` 这类冗余字段。**

报名列表里要显示活动标题和学生姓名。如果接口只返回 id，前端就要为每一行再查一次 —— 一页 20 条就是 40 次请求。

**所以列表接口要把关联信息带出来。** 这是“接口设计要为页面服务”的一个具体体现。

### 某活动的报名统计

```
GET /api/activities/:id/signup-stats
```

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "quota": 100,
    "approvedCount": 42,
    "pendingCount": 8,
    "rejectedCount": 3,
    "remaining": 58
  }
}
```

**这个接口的用处**：活动详情页顶部的统计数字。**不要用“查一次列表接口然后数长度”的方式** —— 那只数了当前页。

### 审核通过

```
PATCH /api/signups/:id/approve
```

**请求体**：无

**前置条件**：报名状态必须是 `PENDING`，且活动名额未满。

**副作用**（后端在一个事务里完成）：

1. 报名状态改为 `APPROVED`
2. 活动的 `pendingCount` 减 1
3. 活动的 `approvedCount` 加 1
4. 记录审核人和审核时间

**错误**

| 码 | 场景 |
| --- | --- |
| `3002` | 报名状态不是 `PENDING` |
| `2005` | 名额已满 |

### 审核驳回

```
PATCH /api/signups/:id/reject
```

**请求体**

```json
{ "rejectReason": "报名信息与本活动要求不符，本活动仅面向声乐特长学生" }
```

**`rejectReason` 必填，5 到 100 字。**

**副作用**：

1. 报名状态改为 `REJECTED`
2. `pendingCount` 减 1
3. 记录驳回理由、审核人、审核时间

**错误**

| 码 | 场景 |
| --- | --- |
| `3002` | 报名状态不是 `PENDING` |
| `3003` | 驳回理由为空或长度不符合要求 |

### 撤销审核

```
PATCH /api/signups/:id/cancel
```

**请求体**

```json
{ "reason": "审核有误，重新处理" }
```

**副作用**：

1. 报名状态改为 `CANCELLED`
2. 如果原来是 `APPROVED`，`approvedCount` 减 1（**名额被释放**）

**这个接口要单独实现，不要用通用的状态修改接口。** 因为“撤销通过”和“撤销待审核”的副作用完全不同 —— 前者要释放名额，后者不用。

**而且它和[业务规则](/project/rules)里的“名额满了靠判断不靠状态”是配套的**：撤销一条通过，`approvedCount` 降到 `quota` 以下，报名入口自动恢复可用。

### 批量审核（可选）

```
PATCH /api/signups/batch-audit
```

**请求体**

```json
{
  "ids": [301, 302, 303],
  "action": "APPROVE",
  "rejectReason": null
}
```

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "successCount": 2,
    "failCount": 1,
    "failures": [
      { "id": 303, "code": 2005, "message": "名额已满" }
    ]
  }
}
```

**这个接口是可选的。** 如果后端不提供，前端就逐条调用单个审核接口，用 `Promise.allSettled` 收集结果。

| 方案 | 好处 | 代价 |
| --- | --- | --- |
| 后端提供批量接口 | 一次请求，后端能控制事务 | 后端工作量增加 |
| 前端逐条提交 | 后端不用改 | N 条记录发 N 次请求；部分失败时数据处于“部分完成”状态，要跟用户解释清楚 |

**注意批量接口的响应设计**：即使部分失败，**外层 `code` 仍然是 `0`**，因为“批量审核”这个动作执行完成了。哪些成功了、哪些失败了，放在 `data` 里。

**这和“冲突预检”是同一个设计原则**：失败的是“动作”还是“结果”。批量操作的结果就是“有的成功有的失败”，这是一个正常结果。

## 八、场地与场次接口

### 场地列表

```
GET /api/venues
```

**响应中的单条场地对象**

```json
{
  "id": 1,
  "name": "大学生活动中心 报告厅",
  "capacity": 300,
  "location": "活动中心 3 楼",
  "remark": "配投影与音响，需提前一天预约",
  "enabled": true
}
```

**`enabled` 字段**：停用的场地不出现在新增场次的选项里，但历史场次仍然能正确显示它。**不要用删除代替停用** —— 删了场地，历史场次就显示不出场地名了。

### 新增 / 编辑场地

```
POST /api/venues
PUT  /api/venues/:id
```

**请求体**

```json
{
  "name": "大学生活动中心 报告厅",
  "capacity": 300,
  "location": "活动中心 3 楼",
  "remark": "配投影与音响，需提前一天预约"
}
```

**场地名称由后端校验唯一性**，重复返回 `4002`。

前端可以在失焦时查一次重名（体验优化），但**不能只靠前端检查** —— 两个人同时创建同名场地，两边都查不到，都提交成功。

### 启用 / 停用场地

```
PATCH /api/venues/:id/enabled
```

**请求体**

```json
{ "enabled": false }
```

**响应**：`{ "code": 0, "message": "success", "data": null }`

**为什么单独一个接口，不用 `PUT /api/venues/:id`**：编辑接口要求提交完整对象，而启用 / 停用只是一个字段的切换。用 `PATCH` 单独一个接口，前端不用先查一次详情再提交。

**和“下架活动”是同一个模式**：状态是流程，启用是标记，两者分开。

**停用之后的三个影响：**

| 影响 | 说明 |
| --- | --- |
| 不出现在新增场次的场地下拉里 | 已经安排的场次不受影响 |
| 历史场次仍能正确显示场地名 | **所以不能把“停用”做成“删除”** |
| 可以随时启用回来 | |

**错误**

| 码 | 场景 |
| --- | --- |
| `4001` | 场地不存在 |

### 场次列表

```
GET /api/sessions?activityId=42
```

**响应中的单条场次对象**

```json
{
  "id": 501,
  "activityId": 42,
  "activityTitle": "2026 春季校园歌手大赛",
  "venueId": 1,
  "venueName": "大学生活动中心 报告厅",
  "startTime": "2026-04-10 14:00:00",
  "endTime": "2026-04-10 17:00:00",
  "status": "SCHEDULED",
  "statusName": "已安排",
  "remark": "初赛"
}
```

### 新增 / 编辑场次

```
POST /api/sessions
PUT  /api/sessions/:id
```

**请求体**

```json
{
  "activityId": 42,
  "venueId": 1,
  "startTime": "2026-04-10 14:00:00",
  "endTime": "2026-04-10 17:00:00",
  "remark": "初赛"
}
```

**校验**：

| 校验项 | 规则 | 错误码 |
| --- | --- | --- |
| 时间范围 | `endTime` 必须晚于 `startTime` | `4004` |
| 场地容量 | 参加人数不能超过场地容量（可选） | `4004` |
| 时段冲突 | 同场地同时段不能重叠（边界相接不算） | `4003` |
| 活动状态 | 已下架或已结束的活动不能排场次 | `2002` |

**编辑时要排除自己**，否则会出现“自己和自己冲突”。见[业务规则](/project/rules)。

### 取消场次

```
PATCH /api/sessions/:id/cancel
```

**请求体**

```json
{ "reason": "场地临时被占用，改期处理" }
```

**响应**：`{ "code": 0, "message": "success", "data": null }`

**取消之后该时段被释放**，可以安排新的场次。**这是“取消”和“删除”的区别** —— 取消保留记录（历史可查），删除会让数据消失。

**冲突检测时必须跳过已取消的场次。** 漏了这一条，组织者取消了一个场次想重新安排，系统会说“时段冲突”，他会很困惑 —— 我明明取消了。见[业务规则](/project/rules)。

**错误**

| 码 | 场景 |
| --- | --- |
| `4001` | 场次不存在 |
| `4005` | 场次已结束，不能取消 |

### 冲突检测（预检）

```
POST /api/sessions/check-conflict
```

**请求体**

```json
{
  "sessionId": null,
  "venueId": 1,
  "startTime": "2026-04-10 14:00:00",
  "endTime": "2026-04-10 17:00:00"
}
```

`sessionId` 为 `null` 表示新增，有值表示编辑（后端据此排除自己）。

**响应（不冲突）**

```json
{ "code": 0, "message": "success", "data": { "conflict": false } }
```

**响应（冲突）**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "conflict": true,
    "conflicts": [
      {
        "id": 502,
        "activityTitle": "程序设计竞赛",
        "startTime": "2026-04-10 15:00:00",
        "endTime": "2026-04-10 18:00:00"
      }
    ]
  }
}
```

**注意这个接口的“冲突”返回的是 `code: 0`（成功）。** 因为“检测”这个动作本身成功了，检测出冲突是一个正常结果，不是错误。

**这是一个值得讲的设计点**：什么时候用错误码，什么时候用成功响应里的标记？

| 情况 | 用哪种 | 为什么 |
| --- | --- | --- |
| 检测出冲突（预检接口） | 成功响应 + `conflict: true` | 检测动作成功了，结果是“有冲突” |
| 真的提交一个冲突的场次 | 错误码 `4003` | 提交动作失败了 |

**区分标准：失败的是“动作”还是“结果”。**

## 九、数据看板接口

### 统计概览

```
GET /api/dashboard/overview
```

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "activityTotal": 36,
    "activityByStatus": {
      "DRAFT": 5,
      "SIGNING": 12,
      "SIGNUP_CLOSED": 6,
      "FINISHED": 13
    },
    "signupTotal": 1284,
    "signupPending": 47,
    "approvedTotal": 936,
    "quotaUsageRate": 0.73,
    "venueTotal": 8,
    "venueUsageToday": 3
  }
}
```

**权限**：组织者看到的是只统计自己活动的数据，审核员看到全部。**过滤在后端做。**

**注意 `quotaUsageRate`（名额使用率）。**

计算方式是 `所有活动的 approvedCount 之和 / 所有活动的 quota 之和`，还是 `approveCount / quota` 逐活动算完再平均？

**这两种算法结果不同。** 举例：一个活动名额 10 人、通过 10 人（100%）；另一个活动名额 1000 人、通过 100 人（10%）。

- 求和再除：`110 / 1010 ≈ 10.9%`
- 逐活动平均：`(100% + 10%) / 2 = 55%`

**差别巨大。** 求和的算法反映“整体资源用了多少”，平均的算法反映“活动平均火爆程度”。

**这一条必须和需求方确认。** 课程项目用**求和再除**（更有业务意义），并在接口文档里写明算法。

### 近期活动

```
GET /api/dashboard/recent-activities?limit=5
```

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": [
    { "id": 42, "title": "2026 春季校园歌手大赛", "status": "SIGNING", "approvedCount": 42, "quota": 100 },
    { "id": 41, "title": "程序设计竞赛", "status": "DRAFT", "approvedCount": 0, "quota": 60 }
  ]
}
```

**按 `updatedAt` 倒序**，取最近更新的几条。

### 待办事项

```
GET /api/dashboard/todos
```

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "pendingSignupCount": 47,
    "endingSoonActivities": [
      { "id": 42, "title": "2026 春季校园歌手大赛", "signupDeadline": "2026-04-01 18:00:00" }
    ],
    "conflictSessions": []
  }
}
```

**这个接口值得单独设计。** 看板不只是一堆数字，它的价值在于告诉用户“现在该做什么”。

| 字段 | 含义 | 引导的动作 |
| --- | --- | --- |
| `pendingSignupCount` | 有多少报名在等审核 | 点击进报名列表，按待审核筛选 |
| `endingSoonActivities` | 48 小时内要截止报名的活动 | 提醒组织者关注 |
| `conflictSessions` | 有冲突的场次（如果允许先保存后解决） | 点击进冲突场次列表 |

**“待办”比“统计”更有价值** —— 统计是给上级看的，待办是给使用者用的。

::: details 看板的接口该怎么拆
三个候选方案：

| 方案 | 怎么做 | 优点 | 缺点 |
| --- | --- | --- | --- |
| 一个接口 | 所有数据一次返回 | 一次请求，首屏快 | 接口耦合，改一处影响全部 |
| 三个接口 | 按上面拆成 overview / recent / todos | 职责清晰，可分开缓存 | 三次请求 |
| 一个接口 + 参数 | `/dashboard?part=overview` | 灵活 | 前端要判断请求几次，复杂度上升 |

**推荐三个接口。** 三个请求可以用 `Promise.all` 并行发出，总耗时约等于最慢的那个，不会明显变慢。

**而且分开之后，如果“近期活动”出问题，看板的其他部分还能正常显示。** 这是容错上的好处 —— 一个接口挂了不至于整页空白。

```js
// 并行请求，各自处理失败
const [overview, recent, todos] = await Promise.allSettled([
  getOverview(), getRecentActivities(), getTodos()
])
```

**注意用 `Promise.allSettled` 而不是 `Promise.all`**，这样某一个失败不会导致全部失败。
:::

## 十、学生端接口

这一章是**用户端（uni-app）专用的接口**。前面第五章到第九章是管理端的接口，用户端只用到其中的登录接口，其余都需要单独一组。

**先说清共同点，下面不重复：** 响应结构（`code` 加 `message` 加 `data`）、业务码、`Authorization: Bearer <token>` 鉴权、分页参数与返回结构、失败时一律 HTTP 200 靠 `code` 区分 —— 全部沿用第二章到第四章的约定。

### 为什么单独开一组 `/student`

用户端和管理端看的是同一批数据，用同一批接口不行吗？**三处不行：**

| 差异 | 管理端 | 用户端 |
| --- | --- | --- |
| 能看到哪些活动 | 草稿、已下架、全部状态 | **只看得到已发布且未下架的** |
| 权限 | 组织者只能看自己的 | 学生看所有已发布的 |
| 字段 | 组织者姓名、待审核数这些内部信息 | 学生不需要，也不该看到 |

**把过滤做在同一个接口的参数里，风险在于忘了传参数就漏数据。** 分开成两组路径，后端在路由层就把权限隔开了 —— 用户端的 token 根本访问不到 `/api/activities`。

**登录接口是共用的**：`POST /api/auth/login` 管理端和学生端用同一个，因为它们都返回 `{ token, userInfo }`，区别只在 `userInfo.role` 是 `ORGANIZER`、`AUDITOR` 还是 `STUDENT`。

### 学生端活动列表

```
GET /api/student/activities?page=1&pageSize=10&keyword=歌手&type=COMPETITION&status=SIGNING
```

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `page` | number | 否 | 页码，从 1 开始，默认 1 |
| `pageSize` | number | 否 | 每页条数，默认 10，最大 50 |
| `keyword` | string | 否 | 按标题模糊搜索 |
| `type` | string | 否 | 活动类型筛选 |
| `status` | string | 否 | 只看某一状态，常用 `SIGNING` |

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "list": [
      {
        "id": 42,
        "title": "2026 春季校园歌手大赛",
        "type": "COMPETITION",
        "organizerName": "校学生会文艺部",
        "quota": 100,
        "approvedCount": 58,
        "signupDeadline": "2026-04-01 18:00:00",
        "status": "SIGNING",
        "coverUrl": "https://cdn.example.edu.cn/activity/42.jpg"
      }
    ],
    "total": 23,
    "page": 1,
    "pageSize": 10
  }
}
```

**三条约定：**

**一、列表里不返回 `description`。** 活动说明可能很长，列表页不需要。**说明放在详情接口里。** 这一条直接影响首屏加载速度 —— 二十条活动各带一段 500 字的说明，响应体会大好几倍。

**二、`coverUrl` 可能是 `null`。** 学生端要处理没有封面的情况，用一张默认图占位。

**三、默认排序是“报名中的在前，然后按报名截止时间升序”。** 学生最关心的是“还能报名的、快截止的”，把已结束的排前面没有意义。**排序规则要写进接口文档**，否则前端不知道要不要自己排。

### 活动详情（学生视角）

```
GET /api/student/activities/{id}
```

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 42,
    "title": "2026 春季校园歌手大赛",
    "type": "COMPETITION",
    "organizerName": "校学生会文艺部",
    "quota": 100,
    "approvedCount": 58,
    "signupDeadline": "2026-04-01 18:00:00",
    "status": "SIGNING",
    "offShelf": false,
    "description": "<p>面向全校在读学生的歌唱比赛……</p>",
    "coverUrl": "https://cdn.example.edu.cn/activity/42.jpg",
    "mySignupStatus": null,
    "sessions": [
      { "id": 8, "startTime": "2026-04-10 14:00:00", "endTime": "2026-04-10 17:00:00", "venueName": "大学生活动中心 201" }
    ]
  }
}
```

**两个学生端特有的字段：**

| 字段 | 说明 |
| --- | --- |
| `mySignupStatus` | 当前登录学生对这个活动的报名状态。`null` 表示没报过。 |
| `sessions` | 已安排的场次。学生想知道什么时候、在哪儿办。 |

**`mySignupStatus` 是为学生端加的。** 有了它，详情页不用额外发一个请求去查“我报过没有”：

```js
// 有 mySignupStatus 时：一个请求就能决定按钮状态
if (data.mySignupStatus && data.mySignupStatus !== 'CANCELLED') {
  // 已报名，按钮显示“查看我的报名”
}

// 没有的话：还得再发一个请求查自己的报名记录，多一次往返
```

**`description` 返回的是 HTML 字符串。** 学生端用 `<rich-text>` 渲染，**不支持复杂 CSS**，所以后端返回的活动说明要用基础标签（`p`、`div`、`span`、`strong`、`img`）。

**未登录也能访问这个接口**，此时 `mySignupStatus` 固定为 `null`。**这一点很重要** —— 学生端的活动列表和详情都允许未登录浏览，只有报名才要求登录。

### 提交报名

```
POST /api/student/signups
```

**请求体**

```json
{
  "activityId": 42,
  "studentNo": "2023010101",
  "studentClass": "软件 2301",
  "remark": "希望安排在下午场"
}
```

**姓名不用传** —— 从登录用户的信息里取。**这是刻意的设计：** 让学生填自己的姓名，等于允许他随便写，审核环节就没有意义了。

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1024,
    "activityId": 42,
    "status": "PENDING",
    "createdAt": "2026-03-20 15:12:33"
  }
}
```

**后端的四道检查**（缺一不可）：

| 顺序 | 检查 | 失败返回 |
| --- | --- | --- |
| 1 | 活动存在且未下架 | `2001` / `2007` |
| 2 | 活动状态是 `SIGNING` | `2007` |
| 3 | 当前时间早于 `signupDeadline` | `2006` |
| 4 | 名额未满 | `2005` |
| 5 | 该学生没有对同一活动的有效报名 | `3004` |

**检查顺序要从便宜到贵。** 查活动状态是一次内存判断，查“是否重复报名”要扫数据库，所以重复报名的检查放在最后。

::: warning 名额的并发问题
两个学生同时提交，都查到“还剩 1 个名额”，然后都通过检查 —— **最后通过审核的是 2 个人，超了。**

**这一段必须在后端用事务加行锁（或乐观锁）处理，前端做什么都防不住。** 前端能做的只有：拿到 `2005` 时刷新一下名额显示，让用户看到真实情况。

**前端不要试图用“先查名额再提交”来避免这个问题** —— 那是两次请求，中间的时间差只会让问题更明显。
:::

### 我的报名列表

```
GET /api/student/signups/mine?page=1&pageSize=10&status=PENDING
```

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "list": [
      {
        "id": 1024,
        "activityId": 42,
        "activityTitle": "2026 春季校园歌手大赛",
        "activityStatus": "SIGNING",
        "activityStartTime": "2026-04-10 14:00:00",
        "venueName": "大学生活动中心 201",
        "status": "APPROVED",
        "remark": "希望安排在下午场",
        "rejectReason": null,
        "auditorName": "李老师",
        "auditedAt": "2026-03-21 09:30:00",
        "createdAt": "2026-03-20 15:12:33"
      }
    ],
    "total": 5,
    "page": 1,
    "pageSize": 10
  }
}
```

**两个字段是特意加的：**

| 字段 | 为什么 |
| --- | --- |
| `activityStatus` | 学生要知道活动还开着没 —— 已通过但活动结束了，和已通过且活动还开着，处理不同 |
| `activityStartTime` 加 `venueName` | 已通过的学生最关心“什么时候、在哪儿”，不该让他再点进详情页查 |

**`rejectReason` 只在 `status` 为 `REJECTED` 时有值。** 这个信息要在列表里就显示出来 —— 学生点进“我的报名”，最想看的就是“为什么被拒了”。

### 取消报名

```
PUT /api/student/signups/{id}/cancel
```

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": { "id": 1024, "status": "CANCELLED" }
}
```

**可取消的条件：**

| 条件 | 不满足时返回 |
| --- | --- |
| 报名记录属于当前登录学生 | `1002` |
| 当前状态是 `PENDING` 或 `APPROVED` | `3002` |
| 关联活动不是 `FINISHED` | `3002` |

**取消后名额会被释放。** 已通过（`APPROVED`）的报名取消后，`approvedCount` 要减一 —— **这是后端的责任，但前端要在取消成功后刷新名额显示**，否则用户看到的是过期数据。

**用 `PUT` 而不是 `DELETE`。** 取消不是删除记录 —— 记录还在，状态变成了 `CANCELLED`。**用 `DELETE` 的语义会让后端不好做审计（谁在什么时候取消的）。**

### 微信小程序登录

```
POST /api/auth/weixin
```

**请求体**

```json
{ "code": "081Kf7Ga1abcDEF2xyz" }
```

这里的 `code` 是小程序端 `uni.login()` 拿到的临时凭证，**不是业务码那个 `code`**（同一个词，两个含义，写文档时要写清楚，否则接口评审时一定会有人问）。

**响应** 与管理端登录一致：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "userInfo": {
      "id": 501,
      "username": null,
      "realName": "张同学",
      "role": "STUDENT",
      "studentNo": "2023010101",
      "studentClass": "软件 2301"
    }
  }
}
```

::: danger AppSecret 只能在服务端
完整链路是：小程序拿 `code` → 发给后端 → **后端带着 `code` 和 `AppSecret` 调微信的 `code2session` 接口** → 换到 `openid` → 后端查或建用户 → 签发自己的 token。

**`AppSecret` 绝不能出现在前端代码里。** 它等同于小程序的最高权限，泄露了别人就能以你的小程序身份调微信接口。**前端也不需要知道 `openid`** —— 那是后端和微信之间的事。
:::

**首次登录时后端自动建用户**，姓名等信息可以后续让学生补全。**不要指望微信能给姓名和学号** —— `wx.getUserProfile` 这类接口能拿到的信息非常有限，学号必须让学生自己填或从教务系统同步。

### 这一章的接口一览

| 接口 | 方法 | 需要登录 | 用途 |
| --- | --- | --- | --- |
| `/api/student/activities` | GET | 否 | 活动列表 |
| `/api/student/activities/{id}` | GET | 否 | 活动详情 |
| `/api/student/signups` | POST | 是 | 提交报名 |
| `/api/student/signups/mine` | GET | 是 | 我的报名 |
| `/api/student/signups/{id}/cancel` | PUT | 是 | 取消报名 |
| `/api/auth/login` | POST | 否 | 账号密码登录（与管理端共用） |
| `/api/auth/weixin` | POST | 否 | 微信小程序登录 |

**两个不需要登录的接口是刻意留着的。** 让学生先看到有什么活动，再决定要不要登录 —— 比一进来就弹登录墙的转化率高得多。

## 十一、通用约定

### 什么时候用 PUT，什么时候用 PATCH

| 方法 | 语义 | 本项目的用法 |
| --- | --- | --- |
| `PUT` | 整体替换资源 | 编辑活动、编辑场地、编辑场次（都是提交完整对象） |
| `PATCH` | 部分修改 | 发布活动、下架、审核通过 / 驳回 / 撤销 |

**判断方法**：提交的数据是“完整对象”还是“只改一个字段”？

**注意 `PUT` 要求客户端提交完整对象**，没传的字段应该被清空或被后端保留 —— 这一点必须和后端约定清楚。

**课程项目建议**：编辑接口的 `PUT` 采用“只更新传了的字段”的宽松语义。**严格语义会带来很多麻烦**（比如编辑时分两次提交会互相覆盖）。

### 什么时候用错误码，什么时候用成功响应里的标记

前面“冲突预检”那一段讲过。再补两个例子：

| 场景 | 用哪种 | 理由 |
| --- | --- | --- |
| 检查活动标题是否重复 | 成功响应 + `{ exists: true }` | 检查动作成功了 |
| 提交一个重复的标题 | 错误码 `4002` | 提交动作失败了 |
| 获取名额使用情况 | 成功响应 | 查询动作总是成功的 |
| 给名额已满的活动安排场次 | 错误码 `2005` | 提交动作失败了 |

**一句话标准：结果“有 / 无”的是查询，用成功响应；结果“行 / 不行”的是提交，用错误码。**

### 时间范围查询

场次列表和报名列表都可能需要按时间范围筛：

```
GET /api/sessions?startDate=2026-04-01&endDate=2026-04-30
```

**约定：日期范围是闭区间，包含首尾两天。** `startDate=2026-04-01&endDate=2026-04-30` 表示 4 月 1 日 00:00:00 到 4 月 30 日 23:59:59。

**这一条要写清楚。** “含不含最后一天”理解不一致，会导致少显示一天的数据 —— 而这种问题很难被发现。

### 布尔值的传递

**约定：布尔字段用 `true` / `false`，不用 `0` / `1`，不用 `'true'` / `'false'` 字符串。**

**前端要做的转换**：从 URL query 或 `localStorage` 读出来的值都是字符串，传给接口前要转：

```js
// utils/format.js
export function toBool(value) {
  return value === true || value === 1 || value === '1' || value === 'true'
}
```

**注意 `Boolean('false')` 是 `true`。** 这是一个经典的坑。

## 十二、这份约定怎么维护

### 改动流程

接口约定是双方的合同，**任何一方改动都要通知对方**。

| 改动类型 | 流程 |
| --- | --- |
| 新增接口或字段 | 直接加，通知对方 |
| 修改字段名或类型 | **必须提前沟通**，双方排期 |
| 删除接口或字段 | **必须确认没人再用** |
| 修改错误码含义 | **禁止直接改**，新增一个码 |

**最后一条要强调**：错误码是稳定契约。把 `2005` 的含义从“名额已满”改成别的，前端会按旧的逻辑处理，产生难以发现的 bug。

**要改就新增一个码，旧码标记为废弃。**

### 前端怎么核对

前端写完 `api` 层之后，对着这份文档检查：

| 检查项 | 怎么核对 |
| --- | --- |
| 路径和方法 | 逐个对比 `api/*.js` 里的调用 |
| 参数名 | 检查请求体里的字段名是不是和文档一致 |
| 参数类型 | 特别是布尔和数字，别传字符串 |
| 返回结构取值 | 列表取 `list` / `total`，不是 `records` / `totalCount` |
| 错误码处理 | 有没有对 `2003`、`2005`、`4003` 这类业务错误单独处理 |

**最后一项最容易被忽略。** 只写了 `ElMessage.error(message)` 的话，`4003` 冲突的详细信息就丢了 —— 用户只看到“时段冲突”，不知道和谁冲突。

## 小结

- **基础路径 `/api`，开发和生产的区别只在转发方式**（Vite 代理 vs Nginx），前端代码不用改。
- **统一响应结构 `{ code, message, data }`**，业务失败靠 `code` 判断，不靠 HTTP 状态码。
- **先确认“失败时用 HTTP 200 还是 4xx”**，这决定了拦截器怎么写。
- **前端按 `code` 判断，不按 `message`。** 文案会变，码不会。
- **`total` 必须是总条数**，前端分页器靠它算页数。
- **`page` 从 1 开始**，不是 0。
- **列表接口要把关联字段带出来**（`activityTitle`、`studentName`），否则前端要为每行再查一次。
- **权限过滤在后端做**，前端不传 `organizerId`。
- **`canEdit` 这类权限布尔值推荐后端返回**，但前端仍要理解规则内容。
- **`approvedCount` 必须后端在事务里维护**，前端只读。
- **`PUT` 是整体替换，`PATCH` 是部分修改。** 发布、下架、审核用 `PATCH`。
- **“查询有没有”用成功响应， “提交能不能”用错误码。**
- **冲突预检返回 `code: 0` + `conflict: true`**，因为检测动作本身成功了。
- **错误码只增不改。** 改含义是禁止的。
- **`4003` 冲突要带回冲突场次的信息**，否则前端只能提示一句没有信息量的话。

---

上一页：[业务规则与状态流转](/project/rules) · 下一页：[目录结构与命名约定](/project/structure)

