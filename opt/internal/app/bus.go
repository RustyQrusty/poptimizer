package app

import (
	"context"
	"fmt"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/port/selected"
	"sync"
	"time"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
	"github.com/WLM1ke/poptimizer/opt/pkg/clients"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
	"go.mongodb.org/mongo-driver/mongo"
)

const (
	_eventTimeout = time.Minute * 5
	_errorTimeout = time.Second * 30
)

// EventBus - шина событий. Позволяет публиковать их и подписываться на заданный топик.
type EventBus struct {
	logger   *lgr.Logger
	telegram *clients.Telegram

	handlers []domain.EventHandler
	inbox    chan domain.Event

	lock    sync.RWMutex
	stopped bool
}

// PrepareEventBus создает шину сообщений и настраивает все обработчики.
func PrepareEventBus(
	logger *lgr.Logger,
	telegram *clients.Telegram,
	database *mongo.Client,
	iss *gomoex.ISSClient,
) *EventBus {
	bus := EventBus{
		logger:   logger,
		telegram: telegram,
		inbox:    make(chan domain.Event),
	}

	bus.Subscribe(data.NewTradingDateHandler(&bus, domain.NewRepo[time.Time](database), iss))
	bus.Subscribe(data.NewUSDHandler(&bus, domain.NewRepo[data.Rows[data.USD]](database), iss))
	bus.Subscribe(data.NewSecuritiesHandler(&bus, domain.NewRepo[data.Rows[data.Security]](database), iss))

	bus.Subscribe(selected.NewHandler(domain.NewRepo[selected.Tickers](database)))

	return &bus
}

// Subscribe регистрирует обработчик для событий заданного топика.
func (e *EventBus) Subscribe(handler domain.EventHandler) {
	e.logger.Infof("registered handler for %s", handler)

	e.handlers = append(e.handlers, handler)
}

// Run запускает шину.
//
// Запуск допускается один раз. События обрабатываются конкурентно.
func (e *EventBus) Run(ctx context.Context) error {
	e.logger.Infof("started")
	defer e.logger.Infof("stopped")

	var waitGroup sync.WaitGroup
	defer waitGroup.Wait()

	for {
		select {
		case event := <-e.inbox:
			waitGroup.Add(1)

			go func() {
				defer waitGroup.Done()

				e.handle(event)
			}()
		case <-ctx.Done():
			e.stop()

			return nil
		}
	}
}

func (e *EventBus) stop() {
	e.lock.Lock()
	defer e.lock.Unlock()

	e.stopped = true
	close(e.inbox)
}

func (e *EventBus) handle(event domain.Event) {
	e.logger.Infof("handling %s", event)

	var waitGroup sync.WaitGroup
	defer waitGroup.Wait()

	for _, h := range e.handlers {
		if h.Match(event) {
			handler := h

			waitGroup.Add(1)

			go func() {
				defer waitGroup.Done()

				ctx, cancel := context.WithTimeout(context.Background(), _eventTimeout)
				defer cancel()

				e.logErr(handler.Handle(ctx, event))
			}()
		}
	}
}

// Publish публикует событие в шину сообщений для рассылки подписчикам.
func (e *EventBus) Publish(event domain.Event) {
	e.lock.RLock()
	defer e.lock.RUnlock()

	if e.stopped {
		e.logErr(fmt.Errorf("stopped before handling event %s", event))

		return
	}

	e.inbox <- event
}

func (e *EventBus) logErr(err error) {
	if err == nil {
		return
	}

	e.logger.Warnf("can't handle event -> %s", err)

	ctx, cancel := context.WithTimeout(context.Background(), _errorTimeout)
	defer cancel()

	if err = e.telegram.Send(ctx, err.Error()); err != nil {
		e.logger.Warnf("can't send notification -> %s", err)
	}
}