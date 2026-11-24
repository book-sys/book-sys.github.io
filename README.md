# book-sys.github.io
## English

Адреса: https://book-sys.github.io/english/

- `index.html` — увесь застосунок (Today, Tracker, Pimsleur, Homework, Text).
- `data.json` — домашка (`homework`) і текст тижня (`week_text`); його оновлюємо після кожного заняття.
- Позначки й прогрес зберігаються в пам'яті телефона (`localStorage`), як у спорт-календарі.
- Копія прогресу йде в Google-таблицю «English — прогрес» (Диск book@, папка «Особисте»): аркуші Дні, Pimsleur, Домашка, Стан. Пише туди Apps Script (`@OnlyCurrentDoc`, веб-застосунок «для всіх», лише приймає дані); його адреса — `SHEET_URL` в `english/index.html`. Надсилається не частіше ніж раз на 30 с і при закритті застосунку.
