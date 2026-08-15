import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

test('strategy preferences lazily page Skills and display product number tags', () => {
  const source = fs.readFileSync(path.join(root, 'components', 'StrategyPreferences.jsx'), 'utf8')
  assert.match(source, /api\.skills\.list\(\{ q: query\.trim\(\), limit: pageSize, offset \}\)/)
  assert.match(source, /function SkillPicker/)
  assert.match(source, /if \(!expanded\) return undefined/)
  assert.match(source, /ProductNumberTags ids=\{skill\.product_type_ids\}/)
  assert.doesNotMatch(source, /const \[prefs, strats, skills\]/)
  assert.doesNotMatch(source, /function SkillKeywordsEditor/)
  assert.doesNotMatch(source, /Promise\.all\(/)
  assert.match(source, /setItems\(prefs\.product_types \|\| \[\]\)[\s\S]*setLoading\(false\)[\s\S]*api\.tasks\.strategies\(\)/)
})

test('LLM environment variables use a complete select with custom fallback', () => {
  const source = fs.readFileSync(path.join(root, 'components', 'Settings.jsx'), 'utf8')
  assert.match(source, /<select/)
  assert.match(source, /手动输入其他变量名/)
  assert.match(source, /envImportEnabled/)
  assert.doesNotMatch(source, /<datalist/)
})

test('subject cards trust API counts and disambiguate duplicate names', () => {
  const source = fs.readFileSync(path.join(root, 'components', 'SubjectManager.jsx'), 'utf8')
  assert.doesNotMatch(source, /Math\.max\(fromStore, fromBackend\)/)
  assert.match(source, /displayName/)
})

test('subject note page owns its filtered notes instead of sharing dashboard state', () => {
  const source = fs.readFileSync(path.join(root, 'components', 'NotesList.jsx'), 'utf8')
  assert.match(source, /api\.notes\.list\(\{ subject_id: subjectId, summary: true \}\)/)
  assert.match(source, /subjectNotes/)
  assert.doesNotMatch(source, /fetchNotes\(\{ subject_id: subjectId \}\)/)
  assert.match(source, /setSubjectNotes\(\[\]\)/)
  assert.match(source, /setSelectedIds\(new Set\(\)\)/)
  assert.match(source, /setBatchMode\(false\)/)
  assert.match(source, /setBatchProgress\(''\)/)
})

test('strategy preferences hide unimplemented choices', () => {
  const source = fs.readFileSync(path.join(root, 'components', 'StrategyPreferences.jsx'), 'utf8')
  assert.match(source, /implementedStrategies\(strategies\)/)
  assert.doesNotMatch(source, /⚠️/)
})

test('subject cards do not display untracked cumulative hours', () => {
  const manager = fs.readFileSync(path.join(root, 'components', 'SubjectManager.jsx'), 'utf8')
  const dashboard = fs.readFileSync(path.join(root, 'components', 'Dashboard.jsx'), 'utf8')
  assert.doesNotMatch(manager, /total_hours/)
  assert.doesNotMatch(dashboard, /累计.*total_hours/)
})

test('skill installation reports duplicate names to the user', () => {
  const source = fs.readFileSync(path.join(root, 'components', 'SkillsManager.jsx'), 'utf8')
  assert.match(source, /duplicates/)
  assert.match(source, /重复 Skill/)
})

test('generation tasks expose a confirmed delete action', () => {
  const api = fs.readFileSync(path.join(root, 'utils', 'api.js'), 'utf8')
  const source = fs.readFileSync(path.join(root, 'components', 'GenerationTasks.jsx'), 'utf8')
  const store = fs.readFileSync(path.join(root, 'store', 'useStore.js'), 'utf8')
  assert.match(api, /tasks:[\s\S]*delete:/)
  assert.match(source, /Trash2/)
  assert.match(source, /删除任务/)
  assert.match(store, /deletedTaskIds/)
  assert.match(store, /!deletedIds\.has\(task\.id\)/)
  assert.match(store, /deletedTaskIds:[^\n]*filter\(\(id\) => id !== task\.id\)/)
})

test('generation tasks expose subject, product trace, and retry controls', () => {
  const api = fs.readFileSync(path.join(root, 'utils', 'api.js'), 'utf8')
  const source = fs.readFileSync(path.join(root, 'components', 'GenerationTasks.jsx'), 'utf8')
  assert.match(api, /retry:.*tasks\/\$\{id\}\/retry/)
  assert.match(source, /task\.subject_name/)
  assert.match(source, /taskProductsUrl\(task\.id\)/)
  assert.match(source, /retryTask\(task\.id\)/)
  assert.doesNotMatch(source, /创建时间：/)
})

test('V1 note editor hides raw MemoryBear context', () => {
  const source = fs.readFileSync(path.join(root, 'components', 'NoteEditor.jsx'), 'utf8')
  assert.doesNotMatch(source, /mbPreview\.context/)
})

test('per-product strategy has a Skill name and summary search', () => {
  const source = fs.readFileSync(path.join(root, 'components', 'ProductGenerator.jsx'), 'utf8')
  assert.match(source, /function PerProductStrategyModal[\s\S]*const \[skillQuery, setSkillQuery\]/)
  assert.match(source, /\[skill\.name, skill\.description, skill\.category\]/)
  assert.match(source, /visibleSkills\.map/)
  assert.match(source, /ProductNumberTags ids=\{s\.product_type_ids\}/)
})
