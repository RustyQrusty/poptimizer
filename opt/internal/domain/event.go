package domain

import (
	"context"
	"fmt"
	"time"
)

const _timeFormat = "2006-01-02"

// QualifiedID уникальный идентификатор сущности доменной области.
//
// Каждый доменный объект принадлежит к поддомену, группе однородных объектов и имеет уникальный ID в рамках группы.
type QualifiedID struct {
	Sub   string
	Group string
	ID    string
}

// Event представляет событие, с изменением объекта.
type Event struct {
	QualifiedID
	Timestamp time.Time
	Data      any
}

func (e Event) String() string {
	return fmt.Sprintf(
		"Event(%s, %s, %s, %s)",
		e.Sub,
		e.Group,
		e.ID,
		e.Timestamp.Format(_timeFormat),
	)
}

// Publisher - интерфейс для рассылки сообщений.
type Publisher interface {
	Publish(event Event)
}

// EventHandler обработчик события.
type EventHandler interface {
	Match(event Event) bool
	Handle(ctx context.Context, event Event) error
}

// Filter для выбора сообщений.
//
// Если соответсвующее поле не заполнено, то подходит событие с любым значением соответствующего поля.
type Filter struct {
	Sub   string
	Group string
	ID    string
}

func (f Filter) String() string {
	return fmt.Sprintf("Filter(%s, %s, %s)", f.Sub, f.Group, f.ID)
}

// Match проверяет соответствие события фильтру.
func (f Filter) Match(event Event) bool {
	switch {
	case f.ID != "" && event.ID != f.ID:
		return false
	case f.Group != "" && event.Group != f.Group:
		return false
	case f.Sub != "" && event.Sub != f.Sub:
		return false
	}

	return true
}

// Subscriber - интерфейс подписки на сообщения соответствующего топика.
type Subscriber interface {
	Subscribe(EventHandler)
}

// Bus - интерфейс шины сообщений.
type Bus interface {
	Subscriber
	Publisher
}