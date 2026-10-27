# SQLite-память

Использовать Python установленного окружения. Примеры ниже относительны корню исследования; `MEMORY` обозначает путь к поставляемому `scripts/memory.py`, а не отдельный пакет для установки.

```text
python MEMORY init --db research.sqlite --contract contract.json
python MEMORY hypothesis --db research.sqlite --text "Проверяемое утверждение" --rationale "Основание" --test "Что подтвердит/опровергнет"
python MEMORY begin --db research.sqlite --hypothesis 1 --config configs/run01.json --reserve-seconds 300
python MEMORY finish --db research.sqlite --experiment 1 --outcome completed --seconds 215 --metrics results/run01.json --evidence logs/run01.txt predictions/run01.npz code/train.py
python MEMORY finding --db research.sqlite --experiments 1 --text "Наблюдение и его границы" --hypothesis-status uncertain
python MEMORY snapshot --db research.sqlite
python MEMORY freeze --db research.sqlite --decision final_decision.json --evidence runs/best.pt code/evaluate.py
python MEMORY close --db research.sqlite --status budget_exhausted
```

Контракт содержит произвольные дополнительные поля и обязательные:

```json
{
  "question": "Исследовательский вопрос",
  "metric": {"key": "validation_macro_f1", "direction": "maximize", "target": 0.97},
  "max_attempts": 12,
  "max_compute_seconds": 14400,
  "final_evaluation_reserve_seconds": 300
}
```

Добавить определения данных, split hash, диапазон метрики, требование повторений, критерии достижения, срок и токены при наличии. Скрипт не интерпретирует весь контракт и не выдаёт научный вердикт. Верхнеуровневое поле метрики в JSON результата должно совпадать с `metric.key`. `completed` означает завершение попытки, не подтверждение гипотезы.

`begin` возвращает ID попытки. Конфигурация — полный JSON, включая seed, preprocessing, веса, optimizer, расписание и hash кода. Форматированию JSON, порядку ключей и замене чисел 1 на 1.0 не придаётся значение; другие различия сохраняются. После ошибки для идентичной конфигурации: `--retry-reason "Причина"`. После успешного запуска точный дубль запрещён; независимый повтор имеет другое случайное зерно.

Резерв времени учитывается целиком, пока попытка открыта, даже после перезапуска чата. Перед закрытием аварийной попытки проверить её реальный процесс и расход. `finish` не разрешает фактическое время больше резерва без отметки нарушения; данные сохраняются, исследование помечается `budget_violation`, новые запуски блокируются. Оставшиеся попытки можно закрыть с фактическими затратами, а исследование завершить только как invalid или stopped. Финальное оценивание учитывать командой `charge --seconds N --evidence path`; она не расходует попытку обучения и не имеет резервирования — запускать оценщик с внешним timeout по оставшемуся лимиту.

Метрики — JSON-объект с конечными числами; у завершённой попытки обязательна основная метрика. Включать в результат метрики только предназначенной для поиска части данных. Большие файлы в SQLite не вставляются.

`snapshot` возвращает ограниченную сводку: лучшие 5 завершённых попыток, до 10 последних выводов, до 20 гипотез, все незакрытые попытки, число остальных записей и оставшиеся ресурсы. Для адресного чтения: `show --table hypotheses|experiments|findings --id N`.

`freeze` проверяет наличие доказательств, сохраняет их хеши и решение. После фиксации разрешены только закрытие незавершённых попыток, учёт итоговой оценки и завершение исследования; обучение через `begin` запрещено. После close запрещены изменения через интерфейс. События append-only, SQL-триггеры запрещают изменение и удаление событий. Администратор SQLite может обойти это: база не является защитой от намеренно действующего владельца файлов.

`close --status achieved` требует freeze, но не доказывает достижение численного критерия. Перед этим агент/оценщик отдельно проверяет все критерии контракта. Варианты статуса: achieved, budget_exhausted, inconclusive, stopped, invalid. Ограничитель goal/token и время всей работы задаются в среде, а не этим скриптом.
