#!/usr/bin/env bash


echo ===== Install xhyve hypervisor =====
brew install --HEAD xhyve     # from https://github.com/mist64/xhyve


echo ===== Install kubectl =====
brew install kubernetes-cli   # from https://kubernetes.io/docs/tasks/tools/install-kubectl/#install-with-homebrew-on-macos


echo ===== Install minikube =====
brew cask install minikube    # from https://github.com/kubernetes/minikube/releases
