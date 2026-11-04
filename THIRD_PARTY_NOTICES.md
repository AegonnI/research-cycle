# Third-party adaptations / Заимствования

Version 2 is a selective synthesis, not a concatenation or installation of upstream
skill collections. Both language versions express the same adapted procedures.
Pinned commits and SHA-256 digests: [docs/UPSTREAM_SOURCES.json](docs/UPSTREAM_SOURCES.json).

| Source | Selected adaptation / Что взято |
| --- | --- |
| [K-Dense hypothesis-generation](https://github.com/K-Dense-AI/scientific-agent-skills/blob/5f2bc0341354fd5590aef76a533ada1e1e5b4e62/skills/hypothesis-generation/SKILL.md) | Distinguish observation/hypothesis/prediction; rival explanations and discriminating tests. / Разделение утверждений, альтернативы и проверяемые предсказания. |
| [K-Dense scientific-brainstorming](https://github.com/K-Dense-AI/scientific-agent-skills/blob/5f2bc0341354fd5590aef76a533ada1e1e5b4e62/skills/scientific-brainstorming/SKILL.md) | Generate diverse candidates before convergence, keep provenance and negative evidence. / Разнообразие вариантов до отбора, происхождение идей и отрицательные результаты. |
| [K-Dense scientific-critical-thinking](https://github.com/K-Dense-AI/scientific-agent-skills/blob/5f2bc0341354fd5590aef76a533ada1e1e5b4e62/skills/scientific-critical-thinking/SKILL.md) | Independent units, confounding, multiplicity and limits of conclusions. / Независимая единица, смешение факторов, множественный поиск, границы выводов. |
| [Superpowers verification-before-completion](https://github.com/obra/superpowers/blob/2ce8aa15d05bd57213e6f746f953aafb7ded7a8b/skills/verification-before-completion/SKILL.md) | Verify actual artifacts and command results before completion claims. / Проверка реальных файлов, вывода и статуса команд перед заявлением готовности. |
| Our Research Cycle v1 | Contract, SQLite hypotheses/trials/findings, reservations, frozen selection and grouped-data evaluation. / Контракт, SQLite, бюджет и фиксация решения. |

K-Dense and Superpowers are MIT licensed; copyright/permission notices are retained
in [licenses](licenses/). Hermes integration is based on its MIT documentation and
its notice is retained there too. No affiliation or endorsement is implied.

[Karpathy autoresearch program](https://github.com/karpathy/autoresearch/blob/228791fb499afffb54b46200aca536f79142f117/program.md)
was reviewed as conceptual context for automated experimental iteration. Its text/code
is not copied or translated into this distribution; a root LICENSE was not located at
the inspected commit. Bounded candidate search and multi-fidelity selection here are
our own implementation of general research methods.

Not imported: upstream skill dependencies, paid diagram tools, mandatory human/group
facilitation, blanket approval gates, infinite loops, arbitrary workspace resets, or
repeated full audits every turn. Our scope is autonomous bounded computational research.

Не перенесены: внешние зависимости и платные инструменты, обязательные обсуждения с
людьми, бесконечные циклы и проверки всего проекта на каждом ходе. Русский текст —
адаптация выбранных процедур, а не полный перевод исходных коллекций.
