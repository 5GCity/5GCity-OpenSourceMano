# Juju Charm usage and development

This document is intended to provide a brief overview of the components included
in this repository as well as recommendations for how to develop, build, and
publish charms.

Please read the [develper geting started guide](https://jujucharms.com/docs/2.0/developer-getting-started) before proceeding.

## Directory structure

```
.
├── builds
│   └── vpe-router
├── interfaces
├── layers
│   └── vpe-router
└── module-blueprints
```

The source code of a charm is referred to as a "layer". This layer is compiled
into a charm and placed in the `builds/` directory. Interfaces, currently
unused in this context, extend relationships between applications.

## Development workflow
### Prepare your build environment
```
# Source the environment variables JUJU_REPOSITORY, INTERFACE_PATH, and
# LAYER_PATH, which are needed to build a charm. You could also place these
# in your $HOME/.bashrc
$ source juju-env.sh
```
#### Install the `charm` command, either via apt:

```
$ sudo apt install charm
```

or with [snap](http://snapcraft.io/)

```
$ snap install charm --edge
```

To build a charm, simply run `charm build` inside of a layer.
```
$ cd $LAYER_PATH/vpe-router
$ charm build
$ charm deploy $JUJU_REPOSITORY/builds/vpe-router
```

## Publishing to jujucharms.com

Publishing to the Juju Charm store requires a launchpad login. With that, login
to [jujucharms.com](http://www.jujucharms.com/).

Next, you'll use the charm command to publish your compiled charm. This will
put the charm into the store where it can be used by anyone with access.

For example, if I wanted to publish the latest version of the vpe-router charm:

# Step 1: Upload the charm to the "unpublished" channel
```
$ cd $JUJU_REPOSITORY/builds
$ charm push vpe-router/ cs:~aisrael/vpe-router
url: cs:~aisrael/vpe-router-0
channel: unpublished
```

# There are four channels to release a charm: edge, beta, candidate, and stable
```
$ charm release cs:~aisrael/vpe-router-0 --channel=edge
url: cs:~aisrael/vpe-router-0
channel: edge
```
The charm can then be deployed directly from the charm store:
```
$ juju deploy cs:~aisrael/vpe-router --channel=edge
```
