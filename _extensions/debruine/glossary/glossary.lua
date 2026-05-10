-- Glossary.lua
-- Author: Lisa DeBruine

-- Global glossary table (kept for potential server-side use)
globalGlossaryTable = {}

-- Counter for unique table IDs
local glossaryTableCount = 0

-- Helper Functions

local function addHTMLDeps()
    quarto.doc.add_html_dependency({
    name = 'glossary',
    stylesheets = {'glossary.css'},
    scripts = {'glossary.js'}
  })
end

local function kwExists(kwargs, keyword)
    for key, value in pairs(kwargs) do
        if key == keyword then
            return true
        end
    end
    return false
end

local function escapeAttr(s)
  s = tostring(s)
  s = s:gsub("&", "&amp;")
  s = s:gsub('"', "&quot;")
  s = s:gsub("'", "&#39;")
  return s
end

-- Function to sort a Lua table by keys
function sortByKeys(tbl)
    local sortedKeys = {}

    for key, _ in pairs(tbl) do
        table.insert(sortedKeys, key)
    end

    table.sort(sortedKeys)

    local sortedTable = {}
    for _, key in pairs(sortedKeys) do
        sortedTable[key] = tbl[key]
    end

    return sortedTable
end

local function read_metadata_file(fname)
  local metafile = io.open(fname, 'r')
  local content = metafile:read("*a")
  metafile:close()
  local metadata = pandoc.read(content, "markdown").meta
  return metadata
end

local function readGlossary(path)
  local f = io.open(path, "r")
  if not f then
    io.stderr:write("Cannot open file " .. path)
  else
    local lines = f:read("*all")
    f:close()
    return(lines)
  end
end

---Merge user provided options with defaults
---@param userOptions table
local function mergeOptions(userOptions, meta)
  local defaultOptions = {
    path = "glossary.yml",
    popup = "hover",
    show = true,
    add_to_table = true,
    url = ""
  }

  -- override with meta values first
  if meta.glossary ~= nil then
    for k, v in pairs(meta.glossary) do
      local value = pandoc.utils.stringify(v)
      if value == 'true' then value = true end
      if value == 'false' then value = false end
      defaultOptions[k] = value
    end
  end

  -- then override with function keyword values
  if userOptions ~= nil then
    for k, v in pairs(userOptions) do
      local value = pandoc.utils.stringify(v)
      if value == 'true' then value = true end
      if value == 'false' then value = false end
      defaultOptions[k] = value
    end
  end

  return defaultOptions
end


-- Main Glossary Function Shortcode

return {

["glossary"] = function(args, kwargs, meta)

  -- this will only run for HTML documents
  if not quarto.doc.isFormat("html:js") then
    return pandoc.Null()
  end

  addHTMLDeps()

  -- create glossary table
  -- Uses client-side JS to collect terms from already-rendered buttons in the DOM.
  -- This avoids relying on globalGlossaryTable being populated before this shortcode
  -- runs, which is not guaranteed by Quarto's Lua execution order.
  if kwExists(kwargs, "table") then
    glossaryTableCount = glossaryTableCount + 1
    local tableId = "glossary-table-" .. glossaryTableCount

    local gt = "<div id='" .. tableId .. "'></div>\n"
    gt = gt .. "<script>\n"
    gt = gt .. "(function() {\n"
    gt = gt .. "  var el = document.getElementById('" .. tableId .. "');\n"
    gt = gt .. "  if (!el) return;\n"
    -- Select only buttons that have data-def (i.e. add_to_table=true)
    gt = gt .. "  var btns = document.querySelectorAll('button.glossary[data-def]');\n"
    gt = gt .. "  var terms = {};\n"
    gt = gt .. "  btns.forEach(function(btn) {\n"
    gt = gt .. "    var def = btn.getAttribute('data-def');\n"
    -- Extract display text from text nodes only, excluding the hidden .def span
    gt = gt .. "    var display = '';\n"
    gt = gt .. "    btn.childNodes.forEach(function(n) {\n"
    gt = gt .. "      if (n.nodeType === 3) display += n.textContent;\n"
    gt = gt .. "    });\n"
    gt = gt .. "    display = display.trim();\n"
    gt = gt .. "    if (display && def) terms[display.toLowerCase()] = {d: display, def: def};\n"
    gt = gt .. "  });\n"
    gt = gt .. "  var keys = Object.keys(terms).sort();\n"
    gt = gt .. "  if (!keys.length) return;\n"
    gt = gt .. "  var html = \"<table class='glossary_table'><tr><th>Term</th><th>Definition</th></tr>\";\n"
    gt = gt .. "  keys.forEach(function(k) {\n"
    gt = gt .. "    html += '<tr><td>' + terms[k].d + '</td><td>' + terms[k].def + '</td></tr>';\n"
    gt = gt .. "  });\n"
    gt = gt .. "  el.innerHTML = html + '</table>';\n"
    gt = gt .. "})();\n"
    gt = gt .. "</script>"

    return pandoc.RawBlock('html', gt)
  end

  -- or set up in-text term
  local options = mergeOptions(kwargs, meta)

  local rawKey = pandoc.utils.stringify(args[1])
  local term = string.lower(rawKey)

  -- Default display: convert hyphens to spaces and capitalise first letter
  local display = rawKey:gsub("%-", " "):gsub("^%l", string.upper)

  if kwExists(kwargs, "display") then
    display = pandoc.utils.stringify(kwargs.display)
  end

  -- get definition
  local def = ""
  if kwExists(kwargs, "def") then
    def = pandoc.utils.stringify(kwargs.def)
  else
    local metafile = io.open(options.path, 'r')
    local content = "---\n" .. metafile:read("*a") .. "\n---\n"
    metafile:close()
    local glossary = pandoc.read(content, "markdown").meta
    for key, value in pairs(glossary) do
      glossary[string.lower(key)] = value
    end
    if kwExists(glossary, term) then
      def = pandoc.utils.stringify(glossary[term])
    end
  end

  -- add to global table
  if options.add_to_table then
    globalGlossaryTable[term] = def
  end

  -- data-term: always present (used by table builder and dblclick navigation)
  -- data-def: only when add_to_table=true and a definition exists (controls table inclusion)
  -- data-glossary-url: only when url is configured (enables dblclick navigation)
  local termAttr = " data-term='" .. escapeAttr(term) .. "'"
  local defAttr = ""
  if options.add_to_table and def ~= "" then
    defAttr = " data-def='" .. escapeAttr(def) .. "'"
  end
  local urlAttr = ""
  if options.url ~= "" then
    urlAttr = " data-glossary-url='" .. escapeAttr(options.url) .. "'"
  end

  local glosstext
  if options.popup == "hover" then
    glosstext = "<button class='glossary'" .. termAttr .. defAttr .. urlAttr .. " title='" .. escapeAttr(def) .."'>" .. display .. "</button>"
  elseif options.popup == "click" then
    glosstext = "<button class='glossary'" .. termAttr .. defAttr .. urlAttr .. "><span class='def'>" .. def .."</span>" .. display .. "</button>"
  elseif options.popup == "none" then
    glosstext = "<button class='glossary'" .. termAttr .. defAttr .. urlAttr .. ">" .. display .. "</button>"
  end

  return pandoc.RawInline("html", glosstext)

end

}
