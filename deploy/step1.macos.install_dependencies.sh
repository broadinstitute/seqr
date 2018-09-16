#!/usr/bin/env bash

brew update
brew install gcc

echo ===== Install java 1.8 =====
brew tap caskroom/versions
brew cask install java8       # needed to run elasticsearch


echo ===== Install xhyve hypervisor =====
brew install --HEAD xhyve     # from https://github.com/mist64/xhyve


echo ===== Install kubectl =====
brew install kubernetes-cli   # from https://kubernetes.io/docs/tasks/tools/install-kubectl/#install-with-homebrew-on-macos


echo ===== Install minikube =====
brew cask install minikube    # from https://github.com/kubernetes/minikube/releases
