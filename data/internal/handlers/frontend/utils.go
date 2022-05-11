package frontend

import (
	"fmt"
	"html/template"
	"io/fs"
	"net/http"

	"go.mongodb.org/mongo-driver/bson/primitive"
)

const (
	_tickers   = `Tickers`
	_dividends = `Dividends`
)

func createSessionID() string {
	return primitive.NewObjectID().Hex()
}

func extendTemplate(index *template.Template, files fs.FS, pattern string) *template.Template {
	index = template.Must(index.Clone())

	return template.Must(index.ParseFS(files, pattern))
}

func execTemplate(tmpl *template.Template, name string, page interface{}, w http.ResponseWriter) error {
	w.Header().Set("Content-Type", "text/html; charset=UTF-8")

	err := tmpl.ExecuteTemplate(w, name, page)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)

		return fmt.Errorf("can't render template %s -> %w", name, err)
	}

	return nil
}

type page struct {
	Menu      string
	SessionID string
	Sidebar   interface{}
	Main      interface{}
	Status    string
}