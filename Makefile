clean:
	rm -rf work
	mn -c

cli:
	python network.py --cli

measure:
	./measure.sh

plot:
	python -m plotter --measure-dir work/measure --plot-dir work/plot --open-plots

eval: measure plot

.PHONY: clean cli measure plot
