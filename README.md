# AP2 Mandate Verifier (Go)

Проверка подписанных мандатов AP2 на Go — то, чего в экосистеме не было.

## Зачем

На 04.10.2026 в `google-agentic-commerce/AP2`:

| язык | строк | крипто подписи | может проверить мандат |
|---|---|---|---|
| Python | 8 863 | 20 модулей | да |
| **Go** | **2 258** | **0** | **нет** — `FakeJWT` |
| PHP | 39 194 | есть | PR не слит |

Go-семпл не содержит ни строки криптографии:

```
code/samples/go/pkg/roles/merchant_agent/tools.go:31
FakeJWT = "eyJhbGciOiJSUz1NiIsImtpZIwMjQwOTA..."
```

Значит ни одна Go-реализация не может проверить мандат и не может быть протестирована.

Этот проект — первая работающая Go-реализация верификации. **Только стандартная
библиотека**, намеренно: утверждение «Go не может» должно быть опровергнуто без
добавления зависимости.

## Что делает

- Разбирает compact SD-JWT: `header.payload.signature~disc~disc~...~`
- Проверяет подпись ES256 над `header.payload`
- Разрешает раскрытия: `{"...": "<digest>"}` заменяется декодированным объектом
- Извлекает `cnf.jwk` и проверяет, что корень связан с ключом агента
- Проверяет `sd_hash` следующего хопа против `sd_jwt` предыдущего
- Сверяет декодированный мандат с эталонным payload

Формат зафиксирован по эталонному Python SDK, а не по догадке:

```
disclosure digest = base64url(sha256(сырая строка раскрытия))
sd_jwt            = issuer_jwt + "~" + join(disclosures, "~") + "~"
sd_hash           = base64url(sha256(sd_jwt))
```

## Запуск

```bash
go build ./...
go vet ./...
go run ./cmd/verify              # все векторы из vectors/
go test ./...
```

Результат:

```
  OK    open-payment-mandate-card-basic    — chain valid, cnf=agent key, amount 100 USD matches reference
  OK    open-payment-mandate-debit-large   — chain valid, cnf=agent key, amount 50000 USD matches reference
  OK    open-payment-mandate-nonusd        — chain valid, cnf=agent key, amount 25000 BRL matches reference

  total: 3/3 passed verification
```

## Кросс-валидация

Два независимых верификатора на двух языках обязаны дать одинаковый вердикт:

```bash
python3 crosscheck.py
```

```
вектор                                     Python    Go        совпали
────────────────────────────────────────────────────────────────────────
open-payment-mandate-card-basic            ACCEPT    ACCEPT    да
open-payment-mandate-debit-large           ACCEPT    ACCEPT    да
open-payment-mandate-nonusd                ACCEPT    ACCEPT    да
────────────────────────────────────────────────────────────────────────
  совпадений: 3/3, расхождений: 0
```

До появления этой работы кросс-валидация была невозможна: независимой
реализации не существовало.

## Границы

- Покрывает happy path плюс проверку `cnf` и `sd_hash`. **Не** покрывает
  отрицательные векторы (аудитория, подмена суммы) — это следующий шаг.
- Проверка сроков (`iat`/`exp`) не реализована.
- Проверка `expected_aud` **намеренно отсутствует**, как и в эталонном SDK:
  это дефект, о котором идёт речь в ap2-corpus. Когда SDK исправят, сюда
  добавится та же проверка.

Apache-2.0.
