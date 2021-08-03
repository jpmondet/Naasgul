#! /bin/bash

runner_running=$(docker ps | grep -i gitlab-runner)

ci_jobs="black pylint pytest build_api build_toposcrapper build_statscrapper build_frontend"

if [ -z "$runner_running" ]
then
  docker run -d --name gitlab-runner --restart always -v $PWD:$PWD -v /var/run/docker.sock:/var/run/docker.sock gitlab/gitlab-runner:latest
fi

for job in $ci_jobs; do
  echo "$job"
  docker exec -it -w $PWD gitlab-runner gitlab-runner exec docker --docker-volumes /var/run/docker.sock:/var/run/docker.sock "$job"
done
