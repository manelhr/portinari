# ---------------------------- ----------------------------  ---------------------------- ---------------------------- #
# ---------------------------- ----------------------------  ---------------------------- ---------------------------- #
#                                     # / ---------------------------- \ #                                             #
#                                     # | AUTHOR: MANOEL HORTA RIBEIRO | #                                             #
#                                     # \ ---------------------------- / #                                             #
# ---------------------------- ----------------------------  ---------------------------- ---------------------------- #
# ---------------------------- ----------------------------  ---------------------------- ---------------------------- #
from backend.utils.io_handling import Dataset, reads_params, get_config, read_config
from backend.query_maker.get_individuals import get_individuals
from flask import Flask, request, jsonify
from flask_cors import cross_origin

app = Flask(__name__)

# STARTS A DATASET SINGLETON
dataset = Dataset()

# DEBUG VARIABLES
DEBUG_PARAMETERS = True
DEBUG_CONFIG = False


@app.route('/', methods=['POST'])
@cross_origin()
def index():

    response = jsonify({'some': 'data'})

    # Reads the parameters from the query
    nodes, edges, global_attr, outcomes, future_nodes, prediction_attr, id_attr, matching, ds = reads_params(request)

    if DEBUG_PARAMETERS:
        print("prediction attr:", prediction_attr)
        print("future nodes:", future_nodes)
        print("outcomes:", outcomes)
        print("matching:", matching)
        print("globals:", global_attr)
        print("id_attr:", id_attr)
        print("Nodes:", nodes)
        print("Edges:", edges)
        print("dataset:", ds)

    dataset.get_instance(ds)

    # Gets individual
    individuals = get_individuals(nodes, edges, dataset, global_attr, prediction_attr, matching)

    return response


@app.route('/config/', methods=['POST'])
@cross_origin()
def config():
    param = read_config(request)
    cf = get_config(param)
    if DEBUG_CONFIG:
        print(param)
    return cf

if __name__ == "__main__":
    app.run()
