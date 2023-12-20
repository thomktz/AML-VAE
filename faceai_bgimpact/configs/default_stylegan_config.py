config = {
    "dataset": "ffhq_raw",
    "dlr": 0.002,
    "glr": 0.005,
    "mlr": 0.00005,
    "loss": "wgan-gp",
    "latent_dim": 256,
    "w_dim": 256,
    "style_layers": 6,
    "save_interval": 2,
    "image_interval": 50,
    "level_epochs": {
        0: {
            "transition": 0,
            "stabilization": 15,
            "batch_size": 128,
            "lr_lambda_transition": 1.0,
            "lr_lambda_stabilization": 0.5,
        },
        1: {
            "transition": 4,
            "stabilization": 20,
            "batch_size": 128,
            "lr_lambda_transition": 0.9,
            "lr_lambda_stabilization": 0.2,
        },
        2: {
            "transition": 10,
            "stabilization": 40,
            "batch_size": 128,
            "lr_lambda_transition": 0.7,
            "lr_lambda_stabilization": 0.2,
        },
        3: {
            "transition": 15,
            "stabilization": 70,
            "batch_size": 128,
            "lr_lambda_transition": 0.5,
            "lr_lambda_stabilization": 0.07,
        },
        4: {
            "transition": 20,
            "stabilization": 95,
            "batch_size": 64,
            "lr_lambda_transition": 0.5,
            "lr_lambda_stabilization": 0.1,
        },
        5: {
            "transition": 25,
            "stabilization": 100,
            "batch_size": 32,
            "lr_lambda_transition": 0.4,
            "lr_lambda_stabilization": 0.05,
        },
    },
}
