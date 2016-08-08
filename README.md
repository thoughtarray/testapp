# testapp
Ever say to yourself, "Darn, I wish I had a simple HTTP app to test my infrastructure—specifically out-of-app service discovery?"  Well, `testapp` is your answer!  With its patent-pending dependency-chain-calling technology, you too can mimic a deep service call.

## About
`testapp` is a simple Flask application designed to test web apps calling other web apps.  It has three modes: stand-alone mode, static-dependency mode, and dynamic-dependency mode.

### Stand-alone mode
Not very useful.  It just returns what you tell it to.
```sh
testapp --name foo --port 5000
```

### Static-dependency mode
When launching `testapp` in this mode, dependent apps must be hard-configured via arguments.  It might look something like this:
```sh
testapp --name foo --port 5000 \
  --static "bar=http://localhost:5001/"
  --static "baz=http://localhost:5002/"
```

### Dynamic-dependency mode
When launching `testapp` in this mode, dependent apps don't have to be known.  It might look something like this:
```sh
testapp --name foo --port 5000 --dynamic "http://localhost:80/{}/"
# --- or ---
testapp --name foo --port 5000 --dynamic "http://{}.foo.com:80/"
# --- or ---
testapp --name foo --port 5000 --dynamic "http://localhost:80/" \
  --header "X-Route={}"
```
This mode would have to be supported by some kind of proxy.

## How to use
```
testapp [-nprsd]
-n, --name string         Name of instance; default: testapp
-p, --port PORT           Port of instance; default: 80
-r, --return CODE:STRING  Success return; default: 200:NameOfInstance
-s, --static NAME=URL     Starts static-dependency mode (additive property)
-d, --dynamic URL         Starts dynamic-dependency mode; URL may contain "{}"
-h, --header KEY=VALUE    HTTP header (additive property); may use "{}" in dynamic-dependency mode
```

### Stand-alone
The simplest use of `testapp` would be a single instance in stand-alone mode.  This use may be good for testing something such as [Docker](https://www.docker.com/products/docker-engine) or [Habitat](https://www.habitat.sh).

```sh
testapp --name hello --port 5000 --return "200:Hello, world!"

curl -w "\n" "localhost:5000"
# Should return "Hello, world!"
```

### Dependency chain
A more complex use would be to form a static chain:
```sh
# Instance 1
testapp --name foo --port 5000 \
  --static "bar=http://localhost:5001/"

# Instance 2
testapp --name bar --port 5001

curl -w "\n" "localhost:5000"
# Should return "bar"
```
When an instance has a single, static dependency, the default action when called is to call its dependency as opposed to return its name (or --return data).
"bar" was returned because it was the only dependency of the foo `testapp`.

### Complex dependency structures
More complex relational structures such as trees or graphs require a special type of request: a chain-script request.  I know this sound fancy, but it isn't.  Here is an example:
```sh
# Instance 1
testapp --name foo --port 5000 \
  --static "bar=http://localhost:5001/"
  --static "baz=http://localhost:5002/"

# Instance 2
testapp --name bar --port 5001 \
  --static "foo=http://localhost:5000/"
  --static "baz=http://localhost:5002/"

# Instance 3
testapp --name baz --port 5002 \
  --static "bar=http://localhost:5001/"
  --static "foo=http://localhost:5000/"

curl -w "\n" "localhost:5000?chain=bar,baz,foo"
# Should return ["foo", "bar", "baz", "foo"]
```
The query parameter "chain" is a comma-separated script of what each `testapp` should call next.  In the example, the following call chain results:
you -> foo -> bar -> baz -> foo (deepest dependency) -> baz -> bar -> foo -> you

As you can see, the return is a JSON array of each node's return value.

### Dynamic dependencies
The purpose of this mode is to test out various external-to-app service discovery tools that use proxies or DNS.

Assume the use [SmartStack](http://nerds.airbnb.com/smartstack-service-discovery-cloud/) or [Consul Template](https://www.hashicorp.com/blog/introducing-consul-template.html) along with Nginx or HAProxy and proxying via a header:
```sh
# Instance 1
testapp --name foo --port 5000 \
  --dynamic "http://localhost:80/" \
  --header "X-Route={}"

# Instance 2
testapp --name bar --port 5001 \
  --dynamic "http://localhost:80/" \
  --header "X-Route={}"

# Instance 3
testapp --name baz --port 5002 \
  --dynamic "http://localhost:80/" \
  --header "X-Route={}"

curl -w "\n" -H "X-Route: foo" "localhost:80?chain=foo,bar,baz,foo"
# Should return ["foo", "bar", "baz", "foo"]
```
You may notice that the `curl` request is similar to that in the "Complex dependency structures" example.  The main difference is routing to the foo instance with "foo" as the first stop in the chain-script request.  `testapp` will skip calling itself and move onto the next call in the chain.
