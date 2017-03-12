gcloud config set compute/zone us-east1-b

gcloud container clusters create distributed-1 --num-nodes 2 -m n1-standard-4 --preemptible --no-async \
	--disk-size=50 --tags=distributed,anacondascale --enable-autoscaling --min-nodes=2 --max-nodes=3

gcloud container clusters get-credentials distributed-1

# gcloud container clusters resize distributed-1 5 --async
# gcloud container clusters list

# gcloud container clusters delete distributed-1
