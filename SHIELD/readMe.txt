Command Line Usage Instructions:
	Detection only:
		python main.py --mode detect --file path/to/your/input.txt

	Obfuscation + Feedback + Training:
		python main.py --mode obfuscate --file path/to/your/input.txt

	Validate Patterns:
		python pattern_validator.py

	Test Patterns:
		ppython test_pattern.py --label EMAIL --text "Contact john.doe@example.com"

	Training Monitor:
		python training_monitor_gui.py

	Copy Config to spacy training
	python config_to_spacy_training.py --config 'C:\Users\salda\source\repos\Shield Application\config\SamplePIIData.json' --report 'C:\Users\salda\source\repos\Shield Application\data\Samples\SamplePIIData.txt' --out train.spacy
	
	Load Training Data
	python loadTrainingData.py


Success! Created shield-ui at C:\Users\salda\source\repos\Shield Application\shield-ui
	Inside that directory, you can run several commands:

	  npm start
		Starts the development server.

	  npm run build
		Bundles the app into static files for production.

	  npm test
		Starts the test runner.

	  npm run eject
		Removes this tool and copies build dependencies, configuration files
		and scripts into the app directory. If you do this, you can’t go back!

We suggest that you begin by typing:

	  cd shield-ui
	  npm start