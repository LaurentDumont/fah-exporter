docker-build-and-push:
	sudo docker build . -t laurentfdumont/fah-exporter:latest && sudo docker push laurentfdumont/fah-exporter:latest
