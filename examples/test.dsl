# ----------------------------------------
# Global settings
# ----------------------------------------
size 1280 720
fps 30
duration 12.0
opening_duration 3.0
base_image "../inputs/Bloom.png"
audio "../inputs/Bloom.wav"
blob_scale 8
beat_decay 0.35
font "C:\\Windows\\Fonts\\impact.ttf"
font_size 140

# ----------------------------------------
# 1. Light Overlay
# ----------------------------------------
effect light_overlay {
    blob {
        anchor (0.09375, 0.166667)
        color (255, 245, 250)
        cx "int(max(100, min(width - 100, anchor_x + (80 + 50 * sin(t * 0.6 + 0)) * cos(radians((t * 20) % 360 + 0 * 90)))))"
        cy "int(max(100, min(height - 100, anchor_y + (80 + 50 * sin(t * 0.6 + 0)) * sin(radians((t * 20) % 360 + 0 * 90)))))"
        rx "int(180 * (0.9 + 0.1 * sin(t * 0.9 + 0)))"
        ry "int(120 * (0.9 + 0.1 * cos(t * 0.8 + 0)))"
        alpha 110
    }
    blob {
        anchor (0.90625, 0.166667)
        color (245, 255, 255)
        cx "int(max(100, min(width - 100, anchor_x + (80 + 50 * sin(t * 0.6 + 1)) * cos(radians((t * 20) % 360 + 1 * 90)))))"
        cy "int(max(100, min(height - 100, anchor_y + (80 + 50 * sin(t * 0.6 + 1)) * sin(radians((t * 20) % 360 + 1 * 90)))))"
        rx "int(180 * (0.9 + 0.1 * sin(t * 0.9 + 1)))"
        ry "int(120 * (0.9 + 0.1 * cos(t * 0.8 + 1)))"
        alpha 110
    }
    blob {
        anchor (0.09375, 0.833333)
        color (255, 255, 245)
        cx "int(max(100, min(width - 100, anchor_x + (80 + 50 * sin(t * 0.6 + 2)) * cos(radians((t * 20) % 360 + 2 * 90)))))"
        cy "int(max(100, min(height - 100, anchor_y + (80 + 50 * sin(t * 0.6 + 2)) * sin(radians((t * 20) % 360 + 2 * 90)))))"
        rx "int(180 * (0.9 + 0.1 * sin(t * 0.9 + 2)))"
        ry "int(120 * (0.9 + 0.1 * cos(t * 0.8 + 2)))"
        alpha 110
    }
    blob {
        anchor (0.90625, 0.833333)
        color (250, 245, 255)
        cx "int(max(100, min(width - 100, anchor_x + (80 + 50 * sin(t * 0.6 + 3)) * cos(radians((t * 20) % 360 + 3 * 90)))))"
        cy "int(max(100, min(height - 100, anchor_y + (80 + 50 * sin(t * 0.6 + 3)) * sin(radians((t * 20) % 360 + 3 * 90)))))"
        rx "int(180 * (0.9 + 0.1 * sin(t * 0.9 + 3)))"
        ry "int(120 * (0.9 + 0.1 * cos(t * 0.8 + 3)))"
        alpha 110
    }
}

# ----------------------------------------
# 2. Spectrum Bars
# ----------------------------------------
effect spectrum {
    bars 96
    max_height_ratio 0.35
    color (255, 255, 255)
    alpha 150
    boost 1.2
}

# ----------------------------------------
# 3. Colored Smoke
# ----------------------------------------
effect smoke {
    blob {
        anchor (0.09375, 0.166667)
        color (255, 248, 252)
        cx "int(max(80, min(width - 80, anchor_x + 50 * sin(t * (1.6 + 0 * 0.20) + 0 * 1.1 + 0.3) + 30 * cos(t * (0.48 + 0 * 0.08) + 0 * 1.7 + 0.5))))"
        cy "int(max(80, min(height - 80, anchor_y + 50 * cos(t * (1.40 + 0 * 0.16) + 0 * 1.1 + 0.3) + 25 * sin(t * (0.36 + 0 * 0.06) + 0 * 1.7 + 0.5))))"
        rx "int((140 + 70 * dist_ratio) * (0.95 + 0.05 * sin(t * 0.6 + 0 * 0.8)))"
        ry "int((100 + 50 * dist_ratio) * (0.95 + 0.05 * cos(t * 0.5 + 0 * 1.1)))"
        alpha "int(25 + dist_ratio * 90)"
    }
    blob {
        anchor (0.921875, 0.125)
        color (255, 170, 200)
        cx "int(max(80, min(width - 80, anchor_x + 50 * sin(t * (1.6 + 1 * 0.20) + 1 * 1.1 + 0.3) + 30 * cos(t * (0.48 + 1 * 0.08) + 1 * 1.7 + 0.5))))"
        cy "int(max(80, min(height - 80, anchor_y + 50 * cos(t * (1.40 + 1 * 0.16) + 1 * 1.1 + 0.3) + 25 * sin(t * (0.36 + 1 * 0.06) + 1 * 1.7 + 0.5))))"
        rx "int((140 + 70 * dist_ratio) * (0.95 + 0.05 * sin(t * 0.6 + 1 * 0.8)))"
        ry "int((100 + 50 * dist_ratio) * (0.95 + 0.05 * cos(t * 0.5 + 1 * 1.1)))"
        alpha "int(25 + dist_ratio * 90)"
    }
    blob {
        anchor (0.0703125, 0.861111)
        color (200, 170, 255)
        cx "int(max(80, min(width - 80, anchor_x + 50 * sin(t * (1.6 + 2 * 0.20) + 2 * 1.1 + 0.3) + 30 * cos(t * (0.48 + 2 * 0.08) + 2 * 1.7 + 0.5))))"
        cy "int(max(80, min(height - 80, anchor_y + 50 * cos(t * (1.40 + 2 * 0.16) + 2 * 1.1 + 0.3) + 25 * sin(t * (0.36 + 2 * 0.06) + 2 * 1.7 + 0.5))))"
        rx "int((140 + 70 * dist_ratio) * (0.95 + 0.05 * sin(t * 0.6 + 2 * 0.8)))"
        ry "int((100 + 50 * dist_ratio) * (0.95 + 0.05 * cos(t * 0.5 + 2 * 1.1)))"
        alpha "int(25 + dist_ratio * 90)"
    }
    blob {
        anchor (0.90625, 0.833333)
        color (140, 220, 255)
        cx "int(max(80, min(width - 80, anchor_x + 50 * sin(t * (1.6 + 3 * 0.20) + 3 * 1.1 + 0.3) + 30 * cos(t * (0.48 + 3 * 0.08) + 3 * 1.7 + 0.5))))"
        cy "int(max(80, min(height - 80, anchor_y + 50 * cos(t * (1.40 + 3 * 0.16) + 3 * 1.1 + 0.3) + 25 * sin(t * (0.36 + 3 * 0.06) + 3 * 1.7 + 0.5))))"
        rx "int((140 + 70 * dist_ratio) * (0.95 + 0.05 * sin(t * 0.6 + 3 * 0.8)))"
        ry "int((100 + 50 * dist_ratio) * (0.95 + 0.05 * cos(t * 0.5 + 3 * 1.1)))"
        alpha "int(25 + dist_ratio * 90)"
    }
    blob {
        anchor (0.5625, 0.138889)
        color (255, 160, 160)
        cx "int(max(80, min(width - 80, anchor_x + 50 * sin(t * (1.6 + 4 * 0.20) + 4 * 1.1 + 0.3) + 30 * cos(t * (0.48 + 4 * 0.08) + 4 * 1.7 + 0.5))))"
        cy "int(max(80, min(height - 80, anchor_y + 50 * cos(t * (1.40 + 4 * 0.16) + 4 * 1.1 + 0.3) + 25 * sin(t * (0.36 + 4 * 0.06) + 4 * 1.7 + 0.5))))"
        rx "int((140 + 70 * dist_ratio) * (0.95 + 0.05 * sin(t * 0.6 + 4 * 0.8)))"
        ry "int((100 + 50 * dist_ratio) * (0.95 + 0.05 * cos(t * 0.5 + 4 * 1.1)))"
        alpha "int(25 + dist_ratio * 90)"
    }
    blob {
        anchor (0.453125, 0.861111)
        color (255, 248, 252)
        cx "int(max(80, min(width - 80, anchor_x + 50 * sin(t * (1.6 + 5 * 0.20) + 5 * 1.1 + 0.3) + 30 * cos(t * (0.48 + 5 * 0.08) + 5 * 1.7 + 0.5))))"
        cy "int(max(80, min(height - 80, anchor_y + 50 * cos(t * (1.40 + 5 * 0.16) + 5 * 1.1 + 0.3) + 25 * sin(t * (0.36 + 5 * 0.06) + 5 * 1.7 + 0.5))))"
        rx "int((140 + 70 * dist_ratio) * (0.95 + 0.05 * sin(t * 0.6 + 5 * 0.8)))"
        ry "int((100 + 50 * dist_ratio) * (0.95 + 0.05 * cos(t * 0.5 + 5 * 1.1)))"
        alpha "int(25 + dist_ratio * 90)"
    }
    blob {
        anchor (0.078125, 0.583333)
        color (255, 170, 200)
        cx "int(max(80, min(width - 80, anchor_x + 50 * sin(t * (1.6 + 6 * 0.20) + 6 * 1.1 + 0.3) + 30 * cos(t * (0.48 + 6 * 0.08) + 6 * 1.7 + 0.5))))"
        cy "int(max(80, min(height - 80, anchor_y + 50 * cos(t * (1.40 + 6 * 0.16) + 6 * 1.1 + 0.3) + 25 * sin(t * (0.36 + 6 * 0.06) + 6 * 1.7 + 0.5))))"
        rx "int((140 + 70 * dist_ratio) * (0.95 + 0.05 * sin(t * 0.6 + 6 * 0.8)))"
        ry "int((100 + 50 * dist_ratio) * (0.95 + 0.05 * cos(t * 0.5 + 6 * 1.1)))"
        alpha "int(25 + dist_ratio * 90)"
    }
    blob {
        anchor (0.921875, 0.444444)
        color (200, 170, 255)
        cx "int(max(80, min(width - 80, anchor_x + 50 * sin(t * (1.6 + 7 * 0.20) + 7 * 1.1 + 0.3) + 30 * cos(t * (0.48 + 7 * 0.08) + 7 * 1.7 + 0.5))))"
        cy "int(max(80, min(height - 80, anchor_y + 50 * cos(t * (1.40 + 7 * 0.16) + 7 * 1.1 + 0.3) + 25 * sin(t * (0.36 + 7 * 0.06) + 7 * 1.7 + 0.5))))"
        rx "int((140 + 70 * dist_ratio) * (0.95 + 0.05 * sin(t * 0.6 + 7 * 0.8)))"
        ry "int((100 + 50 * dist_ratio) * (0.95 + 0.05 * cos(t * 0.5 + 7 * 1.1)))"
        alpha "int(25 + dist_ratio * 90)"
    }
    blob {
        anchor (0.140625, 0.25)
        color (140, 220, 255)
        cx "int(max(80, min(width - 80, anchor_x + 50 * sin(t * (1.6 + 8 * 0.20) + 8 * 1.1 + 0.3) + 30 * cos(t * (0.48 + 8 * 0.08) + 8 * 1.7 + 0.5))))"
        cy "int(max(80, min(height - 80, anchor_y + 50 * cos(t * (1.40 + 8 * 0.16) + 8 * 1.1 + 0.3) + 25 * sin(t * (0.36 + 8 * 0.06) + 8 * 1.7 + 0.5))))"
        rx "int((140 + 70 * dist_ratio) * (0.95 + 0.05 * sin(t * 0.6 + 8 * 0.8)))"
        ry "int((100 + 50 * dist_ratio) * (0.95 + 0.05 * cos(t * 0.5 + 8 * 1.1)))"
        alpha "int(25 + dist_ratio * 90)"
    }
    blob {
        anchor (0.859375, 0.75)
        color (255, 160, 160)
        cx "int(max(80, min(width - 80, anchor_x + 50 * sin(t * (1.6 + 9 * 0.20) + 9 * 1.1 + 0.3) + 30 * cos(t * (0.48 + 9 * 0.08) + 9 * 1.7 + 0.5))))"
        cy "int(max(80, min(height - 80, anchor_y + 50 * cos(t * (1.40 + 9 * 0.16) + 9 * 1.1 + 0.3) + 25 * sin(t * (0.36 + 9 * 0.06) + 9 * 1.7 + 0.5))))"
        rx "int((140 + 70 * dist_ratio) * (0.95 + 0.05 * sin(t * 0.6 + 9 * 0.8)))"
        ry "int((100 + 50 * dist_ratio) * (0.95 + 0.05 * cos(t * 0.5 + 9 * 1.1)))"
        alpha "int(25 + dist_ratio * 90)"
    }
}

# ----------------------------------------
# 4. Opening Text
# ----------------------------------------
effect text {
    color (255, 255, 255)
    fade_out_start 2.0
    fade_out_duration 1.0

    line {
        text "TITLE LINE ONE"
        start_time 0.0
        slide_duration 0.9
        fade_duration 0.6
        start_pos (-0.46875, 0.555556)
        end_pos (0.0625, 0.555556)
        easing "ease_out_cubic"
    }

    line {
        text "TITLE LINE TWO"
        start_time 0.35
        slide_duration 0.9
        fade_duration 0.6
        start_pos (-0.390625, 0.75)
        end_pos (0.0625, 0.75)
        easing "ease_out_cubic"
    }
}

# ----------------------------------------
# 5. Glitch
# ----------------------------------------
effect glitch {
    probability 0.20
    corner_ratio 0.22
    max_waves 2
    min_shift 2
    wave_height "8 + random() * 12"
    base_shift "(random() - 0.5) * 10"
}

# ----------------------------------------
# 6. Bass Shake
# ----------------------------------------
effect bass_shake {
    amount 4
    direction both
    decay 0.4
    oscillation_freq 7.0
    rgb_split 2
    zoom 0.03
    idle_amount 1
    idle_freq 1.0
    y_ratio 2
}

# ----------------------------------------
# 7. Sparkle
# ----------------------------------------
effect sparkle {
    # spots = maximum simultaneous sparkles alive on screen at once
    spots 4
    base_radius 25
    radius_var 20
    base_alpha 200
    color (255, 255, 255)
    edge_bias 0.8
    threshold 0.08
    intensity_scale 2.0
    pulse_freq 10.0
    decay 0.35
    central_exclusion 0.4
    brightness_boost 3.5
    fade_mode "exponential"
    alpha_cutoff 0.0
}
