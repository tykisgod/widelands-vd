-- 简体中文译文端到端加载验证
--
-- 验证的是真实链路：tinygettext 解析 .po → 字典命中 → 运行时返回译文。
-- 比静态 po 校验强，能抓出 CRLF、编码、textdomain 路径这类只在运行时暴露的问题。
--
-- 用法（配合 i18n-zh/run-verify.ps1）：
--   widelands.exe --datadir=<repo>/data --scenario=<repo>/test/maps/plain.wmf \
--                 --script=<repo>/i18n-zh/verify_zh.lua --language=zh_CN \
--                 --nosound --fail-on-lua-error --fail-on-errors --homedir=<tmp>

include "scripting/coroutine.lua"

-- 锚点条目：取自 zh_CN.po 中已确认译好的短条目。
-- 任何一条回退成英文，都说明译文加载链路断了。
local ANCHORS = {
   { "No Space",         "空间不足" },
   { "Not enough space", "没有足够的空间" },
   { "No rocks nearby",  "附近没有岩石" },
   { "Status",           "状态" },
   { "New Objective",    "新目标" },
   { "Jan",              "一月" },
   { "Feb",              "二月" },
}

-- 带 msgctxt 消歧的条目走 pgettext，与 _() 是两条不同的查询路径，
-- 只测 _() 无法证明带上下文的条目也能命中。
local CTXT_ANCHORS = {
   { "day_of_month", "Sun", "周日" },
   { "day_of_month", "Sat", "周六" },
}

-- 复数条目走 ngettext。中文 nplurals=1，单复数都应返回 msgstr[0]。
local PLURAL_ANCHORS = {
   { "%u missing add-on", "%u missing add-ons", "%u 个附加内容缺失" },
}

local function has_cjk(s)
   -- UTF-8 下 CJK 统一表意文字起始于 E4..E9 引导字节，够用于冒烟判断
   for i = 1, #s do
      local b = s:byte(i)
      if b >= 0xE4 and b <= 0xE9 then
         return true
      end
   end
   return false
end

run(function()
   sleep(500)

   push_textdomain("widelands")

   local failures = 0
   local checked = 0

   print("=== 简体中文译文加载验证 ===")

   for idx, case in ipairs(ANCHORS) do
      local src, want = case[1], case[2]
      local got = _(src)
      checked = checked + 1

      if got == want then
         print(string.format("  OK    %-20s -> %s", src, got))
      elseif got == src then
         print(string.format("  FAIL  %-20s -> 未翻译，回退为英文原文", src))
         failures = failures + 1
      else
         -- 译文变了但不等于预期：po 被改过，不算链路故障，但要让人看见
         print(string.format("  WARN  %-20s -> %s（预期 %s）", src, got, want))
      end
   end

   for idx, case in ipairs(CTXT_ANCHORS) do
      local ctxt, src, want = case[1], case[2], case[3]
      local got = pgettext(ctxt, src)
      checked = checked + 1
      if got == want then
         print(string.format("  OK    pgettext(%s, %-6s) -> %s", ctxt, src, got))
      elseif got == src then
         print(string.format("  FAIL  pgettext(%s, %s) -> 未翻译，回退为英文原文", ctxt, src))
         failures = failures + 1
      else
         print(string.format("  WARN  pgettext(%s, %s) -> %s（预期 %s）", ctxt, src, got, want))
      end
   end

   for idx, case in ipairs(PLURAL_ANCHORS) do
      local sg, pl, want = case[1], case[2], case[3]
      -- 中文 nplurals=1：n=1 与 n=5 都该返回同一条 msgstr[0]
      local one, many = ngettext(sg, pl, 1), ngettext(sg, pl, 5)
      checked = checked + 1
      if one == want and many == want then
         print(string.format("  OK    ngettext(%s) -> %s", sg, one))
      elseif one == sg or many == pl then
         print(string.format("  FAIL  ngettext(%s) -> 未翻译，回退为英文原文", sg))
         failures = failures + 1
      elseif one ~= many then
         print(string.format("  FAIL  ngettext(%s) -> 单复数返回不同（%s / %s），"
                             .. "中文 nplurals 应为 1", sg, one, many))
         failures = failures + 1
      else
         print(string.format("  WARN  ngettext(%s) -> %s（预期 %s）", sg, one, want))
      end
   end

   -- 独立于锚点的整体性检查：至少要有中文字符真正返回
   local any_cjk = false
   for idx, case in ipairs(ANCHORS) do
      if has_cjk(_(case[1])) then
         any_cjk = true
         break
      end
   end

   if not any_cjk then
      print("  FAIL  没有任何条目返回中文字符——译文加载链路整体失效")
      failures = failures + 1
   end

   pop_textdomain()

   print(string.format("=== 检查 %d 条，失败 %d 条 ===", checked, failures))

   if failures > 0 then
      -- 让 --fail-on-lua-error 捕获，使退出码非零
      error(string.format("译文加载验证失败：%d 条", failures))
   end

   print("# All Tests passed.")

   wl.ui.MapView():close()
end)
