size 640 360
fps 30
base_image "../inputs/Bloom.png"
audio "../inputs/Bloom.wav"

effect spectrum {
    bars 8
    color (255, 255, 255)
    alpha 100
}

effect text {
    line {
        text "TEST"
        start_time 0.0
        start_pos (0.1, 0.5)
        end_pos (0.2, 0.5)
        easing "ease_out_cubic"
    }
}
