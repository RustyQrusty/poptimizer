package selected

import (
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
	"github.com/stretchr/testify/assert"
	"testing"
)

func prepare() Tickers {
	return Tickers{
		"AKRN":  true,
		"GAZP":  true,
		"UPRO":  true,
		"NVTK":  false,
		"RTKM":  false,
		"RTKMP": false,
		"RTKMD": false,
	}
}

func TestTickers_update(t *testing.T) {
	tickers := prepare().update([]data.Security{
		{Ticker: "AKRN"},
		{Ticker: "GMKN"},
		{Ticker: "NVTK"},
		{Ticker: "RTKMP"},
	})

	expected := Tickers{
		"AKRN":  true,
		"GMKN":  false,
		"NVTK":  false,
		"RTKMP": false,
	}

	assert.Equal(t, expected, tickers, "incorrect update of selected tickers")
}

func TestTickers_Selected(t *testing.T) {
	tickers := prepare().Selected()
	out := []string{"AKRN", "GAZP", "UPRO"}

	assert.Equal(t, out, tickers, "wrong selected tickers")
}

func TestTickers_NotSelected(t *testing.T) {
	table := []struct {
		prefix string
		out    []string
	}{
		{"", nil},
		{"n", []string{"NVTK"}},
		{"RT", []string{"RTKM", "RTKMD", "RTKMP"}},
		{"G", []string{}},
	}

	tickers := prepare()

	for _, c := range table {
		assert.Equal(
			t,
			c.out,
			tickers.SearchNotSelected(c.prefix),
			"wrong not selected tickers",
		)
	}
}

func TestTickers_Add(t *testing.T) {
	table := []struct {
		ticker   string
		err      bool
		selected []string
	}{
		{"R", true, []string{"AKRN", "GAZP", "UPRO"}},
		{"AKRN", true, []string{"AKRN", "GAZP", "UPRO"}},
		{"NVTK", false, []string{"AKRN", "GAZP", "NVTK", "UPRO"}},
	}

	for _, c := range table {
		tickers := prepare()
		err := tickers.Add(c.ticker)

		assert.Equal(t, 7, len(tickers), "size of tickers must not change")
		assert.Equal(t, c.err, err != nil, "wrong addition to selected tickers")
		assert.Equal(t, c.selected, tickers.Selected(), "wrong addition to selected tickers")
	}

}

func TestTickers_Remove(t *testing.T) {
	table := []struct {
		ticker   string
		err      bool
		selected []string
	}{
		{"R", true, []string{"AKRN", "GAZP", "UPRO"}},
		{"AKRN", false, []string{"GAZP", "UPRO"}},
		{"NVTK", true, []string{"AKRN", "GAZP", "UPRO"}},
	}

	for _, c := range table {
		tickers := prepare()
		err := tickers.Remove(c.ticker)

		assert.Equal(t, 7, len(tickers), "size of tickers must not change")
		assert.Equal(t, c.err, err != nil, "wrong removal to selected tickers")
		assert.Equal(t, c.selected, tickers.Selected(), "wrong removal to selected tickers")
	}

}