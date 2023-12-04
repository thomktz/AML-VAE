config = {
    "dataset": "ffhq_raw",
    "dlr": 0.0007,
    "glr": 0.001,
    "mlr": 0.00001,
    "loss": "wgan-gp",
    "latent_dim": 256,
    "w_dim": 256,
    "style_layers": 6,
    "save_interval": 2, 
    "image_interval": 50,
    "level_epochs": {
        0: {
            "transition": 0,
            "training": 15,
            "batch_size": 128
        },           
        1: {
            "transition": 4,
            "training": 20,
            "batch_size": 128
        },
        2: {
            "transition": 10,
            "training": 40,
            "batch_size": 128
        },
        3: {
            "transition": 15,
            "training": 60,
            "batch_size": 128
        },
        4: {
            "transition": 25,
            "training": 80,
            "batch_size": 64
        },
        5: {
            "transition": 40,
            "training": 100,
            "batch_size": 32
        }
    }
}